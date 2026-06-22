import asyncio
import logging
import re
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class DeaScraper(BaseScraper):
    """
    Scraper for DEA Aviation (PinpointHQ ATS)
    URL: https://dea.pinpointhq.com/jobs
    """

    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="dea", db_manager=db_manager)
        self.base_url = "https://dea.pinpointhq.com/jobs"
        self.company_name = "DEA Aviation"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            try:
                page, context = await self.setup_stealth_page(browser)
                
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(3000)

                # Extract links directly using JS
                extracted_jobs = await page.evaluate('''() => {
                    const links = Array.from(document.querySelectorAll('a'));
                    return links.map(a => {
                        const href = a.href || "";
                        const title = a.innerText ? a.innerText.trim() : "";
                        const className = a.className || "";
                        return { title, href, className };
                    }).filter(j => j.title.length > 3 && (j.href.includes('/postings/') || j.href.includes('/jobs/')));
                }''')

                # Filter out mobile/desktop duplicate blocks by looking at className or just dedup by href
                seen_hrefs = set()
                unique_jobs = []
                for j in extracted_jobs:
                    # PinpointHQ has hide-sm-block and hide-at-sm-block, they contain the same links
                    # The desktop block usually has the clean title, mobile has concatenated text.
                    # We'll just take the first occurrence of each href and try to get the shortest title
                    href = j["href"]
                    if href not in seen_hrefs:
                        seen_hrefs.add(href)
                        unique_jobs.append(j)
                    else:
                        # If we already saw this href, check if the current title is shorter (cleaner)
                        for existing in unique_jobs:
                            if existing["href"] == href:
                                if len(j["title"]) < len(existing["title"]):
                                    existing["title"] = j["title"]
                                break

                logger.info(f"[{self.site_key}] Found {len(unique_jobs)} unique job postings")

                for job_data in unique_jobs:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    title = job_data["title"].split("\\n")[0].strip()
                    url = job_data["href"]
                    
                    # Sometimes the title contains extra info due to innerText concatenating divs
                    # Example: "Aircraft MechanicEngineeringGamston Airport"
                    # We can clean it by looking for camelCase merging or known departments
                    known_depts = ["Engineering", "Ground Operations", "CAMO", "Pilots", "Finance", "Systems"]
                    for dept in known_depts:
                        if dept in title and title.endswith(dept) == False:
                            idx = title.find(dept)
                            if idx > 5 and title[idx-1].islower() and title[idx].isupper():
                                title = title[:idx]

                    if not self.should_process_job(title):
                        continue

                    job_id_match = re.search(r"/postings/([a-zA-Z0-9-]+)", url)
                    job_id = job_id_match.group(1) if job_id_match else f"dea_{hash(url)}"

                    # Pinpoint URLs are detail pages
                    job = {
                        "job_id": job_id,
                        "title": title,
                        "company": self.company_name,
                        "source": self.site_key,
                        "url": url,
                        "apply_url": url,
                        "location": "Gamston Airport, Retford, UK", # default from pinpoint
                    }

                    jobs.append(job)

            except Exception as e:
                logger.error(f"[{self.site_key}] Global error in fetch_jobs: {e}")
            finally:
                if 'context' in locals():
                    await context.close()
                await browser.close()
                
        return jobs

    async def fetch_job_descriptions(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not jobs:
            return []
            
        logger.info(f"[{self.site_key}] Fetching descriptions for {len(jobs)} jobs...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            try:
                for job in jobs:
                    page, context = await self.setup_stealth_page(browser)
                    try:
                        await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_timeout(2000)

                        desc_el = await page.query_selector(".posting-description, .job-description, .content-block")
                        if desc_el:
                            job["description"] = await desc_el.inner_text()
                        else:
                            job["description"] = await self.extract_description_from_page(page)

                    except Exception as e:
                        logger.warning(f"[{self.site_key}] Failed to fetch description for {job['title']}: {e}")
                    finally:
                        await context.close()
            finally:
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
