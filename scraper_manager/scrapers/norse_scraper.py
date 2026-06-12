import logging
import asyncio
from typing import List, Dict
from urllib.parse import urljoin
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class NorseScraper(BaseScraper):
    """
    Scraper for Norse Atlantic Airways Careers using Playwright.
    URL: https://careers.flynorse.com/jobs
    """

    def __init__(self, config: Dict, db_manager=None):
        super().__init__(config, site_key="norse", db_manager=db_manager)
        self.base_url = "https://careers.flynorse.com/jobs"
        self.company_name = "Norse Atlantic Airways"

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
                await page.wait_for_timeout(5000)

                # Wait for jobs to load
                try:
                    await page.wait_for_selector('a[href*="/jobs/"]', timeout=15000)
                except Exception:
                    logger.warning(f"[{self.site_key}] Timeout waiting for job cards, they might not be available or selector is wrong.")

                # Scroll to load all jobs
                last_height = await page.evaluate("document.body.scrollHeight")
                while True:
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(2000)
                    new_height = await page.evaluate("document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height

                # Extract links
                job_elements = await page.query_selector_all('a[href*="/jobs/"]')
                
                logger.info(f"[{self.site_key}] Found {len(job_elements)} potential job links.")

                seen_urls = set()
                for el in job_elements:
                    href = await el.get_attribute("href")
                    if not href or "department" in href.lower() or "location" in href.lower():
                        continue
                        
                    # Usually Teamtailor job titles are inside the link text or a span
                    # Let's get the inner text or look for a specific class
                    title = await el.inner_text()
                    title = title.split('\n')[0].strip() # Take the first line as title, usually Teamtailor has location on next line
                    
                    if not title or len(title) < 3:
                        title_el = await el.query_selector('span.text-block-base-link, span.font-bold')
                        if title_el:
                            title = await title_el.inner_text()
                            title = title.strip()
                            
                    if not title or len(title) < 3:
                        continue
                        
                    job_url = urljoin(self.base_url, href)
                    if job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)
                    
                    if not self.should_process_job(title):
                        continue

                    # Try to get location
                    location = "Unknown"
                    loc_el = await el.query_selector('div.mt-1 span, span.text-md')
                    if loc_el:
                        loc_text = await loc_el.inner_text()
                        if loc_text:
                            location = loc_text.strip()

                    job_id = f"{self.site_key}_{hash(job_url)}"
                    
                    job = get_job_dict(
                        job_id=job_id,
                        title=title,
                        company=self.company_name,
                        location=location,
                        url=job_url,
                        source_url=self.base_url,
                        description="Norse Atlantic Airways Career Opportunity.",
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
