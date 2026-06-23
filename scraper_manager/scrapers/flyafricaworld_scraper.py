import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class FlyAfricaWorldScraper(BaseScraper):
    """
    Scraper for Africa World Airlines
    URL: https://recruitment.apps-flyafricaworld.com/
    """
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="flyafricaworld", db_manager=db_manager)
        self.base_url = "https://recruitment.apps-flyafricaworld.com/"
        self.company_name = "Africa World Airlines"

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
                    return Array.from(document.querySelectorAll("a")).map(a => {
                        let title = (a.innerText || a.textContent || "").trim();
                        // The job title isn't on the <a> itself (e.g. "View Details & Apply") -
                        // it lives a few levels up in the job card as a separate line, in the
                        // form "Department|Location|Title||Description".
                        if (!title || ["view details", "view details & apply", "apply", "apply now", "read more"].includes(title.toLowerCase())) {
                            let anc = a.parentElement;
                            for (let i = 0; i < 6 && anc; i++) {
                                const lines = (anc.innerText || "").split("\\n").map(s => s.trim()).filter(Boolean);
                                if (lines.length >= 3) {
                                    title = lines[2];
                                    break;
                                }
                                anc = anc.parentElement;
                            }
                        }
                        return { href: a.href, text: title };
                    });
                }''')

                for link in links:
                    if self.max_jobs and len(jobs) >= self.max_jobs: break
                    try:
                        href = link.get("href", "")
                        text = link.get("text", "").strip()
                        if not href or len(text) < 5: continue

                        href_lower = href.lower()
                        if "flyafricaworld" in href_lower and ("jobid=" in href_lower or any(kw in href_lower for kw in ["/job/", "/job-details", "vacancy", "career"])):
                            if text.lower() in ["read more", "apply", "apply now", "view details", "jobs"]:
                                continue
                                
                            job_url = href
                            existing = next((j for j in jobs if j["url"] == job_url), None)
                            if existing:
                                if len(text) > len(existing["title"]): existing["title"] = text
                                continue
                                
                            job_id = f"flyafricaworld_{abs(hash(job_url)) % 10000000}"
                            jobs.append({
                                "job_id": job_id,
                                "title": text,
                                "company": self.company_name,
                                "source": self.site_key,
                                "url": job_url,
                                "apply_url": job_url,
                                "location": "Africa",
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
