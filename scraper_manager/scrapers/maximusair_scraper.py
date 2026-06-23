import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class MaximusAirScraper(BaseScraper):
    """
    Scraper for Maximus Air
    URL: https://www.maximus-air.com/careers
    """
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="maximusair", db_manager=db_manager)
        self.base_url = "https://www.maximus-air.com/careers"
        self.company_name = "Maximus Air"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until="networkidle", timeout=60000)
                await self.random_delay(3, 6)

                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll("a")).map(a => ({
                        href: a.href,
                        text: a.innerText || a.textContent
                    }));
                }''')

                # The top-level /careers page is just a department nav (Antonov &
                # Ilyushin, Engineering, Finance, IT, Operations, Safety/Security/
                # Quality, Sales & Marketing) - actual job postings only appear on
                # these per-department subpages, so they must be visited too.
                department_urls = set()
                for link in links:
                    href = link.get("href", "")
                    if href and "maximus-air.com/careers/" in href.lower():
                        department_urls.add(href)

                visited_urls = {self.base_url}
                pages_to_scan = [self.base_url] + [u for u in department_urls if u not in visited_urls]

                seen_links = list(links)
                for dept_url in department_urls:
                    if dept_url in visited_urls:
                        continue
                    visited_urls.add(dept_url)
                    try:
                        await page.goto(dept_url, wait_until="networkidle", timeout=30000)
                        await self.random_delay(1, 2)
                        dept_links = await page.evaluate('''() => {
                            return Array.from(document.querySelectorAll("a")).map(a => ({
                                href: a.href,
                                text: a.innerText || a.textContent
                            }));
                        }''')
                        seen_links.extend(dept_links)
                    except Exception as e:
                        logger.warning(f"[{self.site_key}] Failed to load department page {dept_url}: {e}")

                for link in seen_links:
                    if self.max_jobs and len(jobs) >= self.max_jobs: break
                    try:
                        href = link.get("href", "")
                        text = link.get("text", "").strip()
                        if not href or len(text) < 5: continue

                        href_lower = href.lower()
                        is_job_link = (
                            "maximus-air.com/careers/" in href_lower
                            and "#" not in href_lower
                            and href_lower not in (u.lower() for u in department_urls)
                            and href_lower.rstrip("/") != self.base_url.lower().rstrip("/")
                        )
                        if is_job_link:
                            if text.lower() in ["read more", "apply", "apply now", "view details", "careers",
                                                  "antonov & ilyushin", "engineering", "finance",
                                                  "information technology", "operations",
                                                  "safety, security & quality", "sales & marketing"]:
                                continue

                            job_url = href
                            existing = next((j for j in jobs if j["url"] == job_url), None)
                            if existing:
                                if len(text) > len(existing["title"]): existing["title"] = text
                                continue

                            job_id = f"maximusair_{abs(hash(job_url)) % 10000000}"
                            jobs.append({
                                "job_id": job_id,
                                "title": text,
                                "company": self.company_name,
                                "source": self.site_key,
                                "url": job_url,
                                "apply_url": job_url,
                                "location": "United Arab Emirates",
                            })
                    except:
                        continue
            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
            finally:
                await context.close()
                await browser.close()
        return jobs

    async def fetch_job_descriptions(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not jobs: return []
        logger.info(f"[{self.site_key}] Fetching descriptions for {len(jobs)} matched jobs...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            for job in jobs:
                try:
                    page, context = await self.setup_stealth_page(browser)
                    await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
                    desc = ""
                    selectors = [".job-description", ".content", "main"]
                    for sel in selectors:
                        el = await page.query_selector(sel)
                        if el:
                            text = await el.inner_text()
                            if len(text) > 100:
                                desc = text.strip()
                                break
                    if not desc:
                        desc = await self.extract_description_from_page(page)
                    job["description"] = desc
                    # Backfill location from the original posting when missing.
                    if not job.get("location") or job.get("location") == "Unknown":
                        _loc = await self.extract_location_from_page(page)
                        if _loc:
                            job["location"] = _loc
                except Exception as e:
                    logger.warning(f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}")
                finally:
                    await context.close()
                await asyncio.sleep(1)
            await browser.close()
        return jobs

    async def run(self):
        self.print_header()
        jobs_raw = await self.fetch_jobs()
        jobs = [get_job_dict(**job) for job in jobs_raw]
        if not jobs: return []
        if self.use_filter and self.filter_manager:
            jobs, _, _ = self.apply_title_filter(jobs)
            if not jobs: return []
        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs: return []
        jobs = await self.fetch_job_descriptions(jobs)
        await self.save_results(jobs)
        return jobs
