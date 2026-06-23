import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class NationalAirlinesScraper(BaseScraper):
    """
    Scraper for National Airlines
    URL: https://www.nationalairlines.com/careers/
    """
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="nationalairlines", db_manager=db_manager)
        self.base_url = "https://www.nationalairlines.com/careers/"
        self.company_name = "National Airlines"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until="networkidle", timeout=60000)
                await self.random_delay(2, 4)

                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll("a")).map(a => ({
                        href: a.href,
                        text: a.innerText || a.textContent
                    }));
                }''')
                
                for link in links:
                    if self.max_jobs and len(jobs) >= self.max_jobs: break
                    try:
                        href = link.get("href", "")
                        text = link.get("text", "").strip()
                        if not href or len(text) < 5: continue
                        
                        href_lower = href.lower()
                        is_own_site_job = "nationalairlines.com" in href_lower and any(kw in href_lower for kw in ["/career/", "job", "vacancy"])
                        is_paylocity_job = "recruiting.paylocity.com" in href_lower and "/jobs/details/" in href_lower
                        if is_own_site_job or is_paylocity_job:
                            if text.lower() in ["read more", "apply", "apply now", "view details", "careers"]:
                                continue
                                
                            job_url = href
                            existing = next((j for j in jobs if j["url"] == job_url), None)
                            if existing:
                                if len(text) > len(existing["title"]): existing["title"] = text
                                continue
                                
                            job_id = f"nationalairlines_{abs(hash(job_url)) % 10000000}"
                            jobs.append({
                                "job_id": job_id,
                                "title": text,
                                "company": self.company_name,
                                "source": self.site_key,
                                "url": job_url,
                                "apply_url": job_url,
                                "location": "USA",
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
