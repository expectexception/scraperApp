import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class SolitairScraper(BaseScraper):
    """
    Scraper for Solitair Holding (Teamtailor)
    URL: https://www.solitairholding.careers/jobs
    """
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="solitair", db_manager=db_manager)
        self.base_url = "https://www.solitairholding.careers/jobs"
        self.company_name = "Solitair Holding"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)

                # Extract links for Teamtailor (jobs are links with classes, often in a list)
                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a')).map(a => ({
                        href: a.href,
                        text: a.innerText || a.textContent
                    })).filter(l => l.href && l.href.includes("/jobs/") && l.text.trim().length > 5);
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
                    
                    # title may include location and department with newlines, let's take the first line as title
                    text_parts = link["text"].strip().split("\\n")
                    title = text_parts[0].strip()
                    
                    location = "Unknown"
                    if len(text_parts) > 1:
                        # e.g. "Air Operations · Dubai (DWC Airport), Dubai South"
                        location_part = text_parts[-1]
                        if "·" in location_part:
                            location = location_part.split("·")[-1].strip()
                        else:
                            location = location_part.strip()
                            
                    job_id = url.split("/jobs/")[-1].split("-")[0]
                    if not job_id:
                        job_id = str(abs(hash(url)) % 10000000)

                    jobs.append({
                        "job_id": f"solitair_{job_id}",
                        "title": title,
                        "company": self.company_name,
                        "source": self.site_key,
                        "url": url,
                        "apply_url": url,
                        "location": location,
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
                    # Common Teamtailor description container
                    desc_el = await page.query_selector("main, .prose, .company-description, .job-description")
                    if desc_el:
                        desc = await desc_el.inner_text()
                    else:
                        desc = await self.extract_description_from_page(page)
                        
                    job["description"] = desc.strip()
                except Exception as e:
                    logger.warning(f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}")
                    job["description"] = ""
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
