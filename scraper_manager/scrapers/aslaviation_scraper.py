import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class AslAviationScraper(BaseScraper):
    """
    Scraper for ASL Aviation Group (Cezanne OnDemand)
    URL: https://cezanneondemand.intervieweb.it/aslaviationgroup/en/career
    """
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="aslaviation", db_manager=db_manager)
        self.base_url = "https://cezanneondemand.intervieweb.it/aslaviationgroup/en/career"
        self.company_name = "ASL Aviation Group"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)

                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a')).map(a => ({
                        href: a.href,
                        text: a.innerText || a.textContent
                    })).filter(l => l.href && l.href.includes("/jobs/") && l.text.trim().length > 5 && !l.text.includes("Apply"));
                }''')

                logger.info(f"[{self.site_key}] Found {len(links)} potential job links.")
                
                seen = set()

                for link in links:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    url = link["href"]
                    if url in seen:
                        continue
                    seen.add(url)
                    
                    title = link["text"].strip()
                    
                    # Extract job_id from URL like /jobs/flight-dispatcher-62476/en/
                    job_id = ""
                    parts = url.split("/")
                    for p in parts:
                        if "-" in p and p.split("-")[-1].isdigit():
                            job_id = p.split("-")[-1]
                            break
                    if not job_id:
                        job_id = str(abs(hash(url)) % 10000000)

                    jobs.append({
                        "job_id": f"aslaviation_{job_id}",
                        "title": title,
                        "company": self.company_name,
                        "source": self.site_key,
                        "url": url,
                        "apply_url": url,
                    })

            except Exception as e:
                logger.error(f"[{self.site_key}] Global error in fetch_jobs: {e}")
            finally:
                await context.close()
                await browser.close()
        return jobs

    async def fetch_job_descriptions(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not jobs: return []
        logger.info(f"[{self.site_key}] Fetching descriptions for {len(jobs)} jobs...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            for job in jobs:
                try:
                    page, context = await self.setup_stealth_page(browser)
                    await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
                    
                    desc = ""
                    desc_el = await page.query_selector(".job_description, main, .container")
                    if desc_el:
                        desc = await desc_el.inner_text()
                    else:
                        desc = await self.extract_description_from_page(page)
                        
                    job["description"] = desc.strip()
                    
                    # Extract location if possible from the page
                    loc_text = await page.evaluate('''() => {
                        const locEl = document.querySelector('.job_location, .location');
                        return locEl ? locEl.innerText.trim() : "";
                    }''')
                    if loc_text:
                        job["location"] = loc_text
                    else:
                        job["location"] = "Unknown"
                        
                except Exception as e:
                    logger.warning(f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}")
                    job["description"] = ""
                    job["location"] = "Unknown"
                finally:
                    await context.close()
                await self.random_delay(1, 2)
            await browser.close()
        return jobs

    async def run(self):
        self.print_header()
        jobs_raw = await self.fetch_jobs()
        jobs = [get_job_dict(**job) for job in jobs_raw]
        if not jobs:
            return []
        if self.use_filter and self.filter_manager:
            jobs, _, _ = self.apply_title_filter(jobs)
            if not jobs:
                return []
        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []
        jobs = await self.fetch_job_descriptions(jobs)
        await self.save_results(jobs)
        return jobs
