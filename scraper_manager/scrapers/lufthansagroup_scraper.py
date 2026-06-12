import logging
import asyncio
from typing import List, Dict
from urllib.parse import urljoin
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class LufthansagroupScraper(BaseScraper):
    """
    Scraper for Lufthansa Group Careers using Playwright.
    URL: https://apply.lufthansagroup.careers/index.php?ac=search_result&search_criterion_channel%5B%5D=12&language=2
    """

    def __init__(self, config: Dict, db_manager=None):
        super().__init__(config, site_key="lufthansagroup", db_manager=db_manager)
        self.base_url = "https://apply.lufthansagroup.careers/index.php?ac=search_result&search_criterion_channel%5B%5D=12&language=2"
        self.company_name = "Lufthansa Group"

    async def fetch_jobs(self) -> List[Dict]:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(10000)

                # Find job rows (adjust selector based on actual render if needed)
                # rexx systems usually use .job-offer, .jobad-title, or similar
                job_elements = await page.query_selector_all('div.job-offer, .job-item, tr.job-row, a[href*="jobad"]')
                
                logger.info(f"[{self.site_key}] Found {len(job_elements)} job elements.")

                for el in job_elements:
                    title_el = await el.query_selector('a')
                    if not title_el:
                        title_el = el if await el.evaluate("el => el.tagName === 'A'") else None

                    if not title_el:
                        continue

                    title = await title_el.inner_text()
                    title = title.strip()
                    href = await title_el.get_attribute("href")
                    
                    if not href or not title:
                        continue

                    job_url = urljoin(self.base_url, href)
                    
                    if not self.should_process_job(title):
                        continue

                    job_id = f"{self.site_key}_{hash(job_url)}"
                    
                    job = get_job_dict(
                        job_id=job_id,
                        title=title,
                        company=self.company_name,
                        location="Unknown",
                        url=job_url,
                        source_url=self.base_url,
                        description="Lufthansa Group Career Opportunity.",
                        apply_url=job_url,
                        source=self.site_key
                    )
                    
                    jobs.append(job)

                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                return jobs

            except Exception as e:
                logger.error(f"[{self.site_key}] Error scraping: {e}")
                return jobs
            finally:
                await browser.close()

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        jobs = [j for j in jobs if j is not None]

        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
