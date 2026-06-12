import logging
import asyncio
from typing import List, Dict
from playwright.async_api import async_playwright
from urllib.parse import urljoin

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class AeroitaliaScraper(BaseScraper):
    """
    Scraper for Aeroitalia Careers using Playwright.
    URL: https://www.aeroitalia.com/en/company/work-with-us
    """

    def __init__(self, config: Dict, db_manager=None):
        super().__init__(config, site_key="aeroitalia", db_manager=db_manager)
        self.base_url = "https://www.aeroitalia.com/en/company/work-with-us"
        self.company_name = "Aeroitalia"

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

                # Look for links containing job or career or work
                job_elements = await page.query_selector_all('a')
                
                logger.info(f"[{self.site_key}] Found {len(job_elements)} total links on page.")

                seen_urls = set()
                for el in job_elements:
                    href = await el.get_attribute("href")
                    if not href:
                        continue
                        
                    # Filter based on common job URL patterns or check the text
                    title = await el.inner_text()
                    title = title.strip()
                    
                    if not title or len(title) < 4:
                        continue
                        
                    if "apply" in title.lower() or "job" in title.lower() or "career" in href.lower() or "work" in href.lower() or "position" in href.lower() or "recruitment" in href.lower():
                        if "policy" in href.lower() or "terms" in href.lower():
                            continue
                            
                        job_url = urljoin(self.base_url, href)
                        
                        if job_url == self.base_url: # ignore the main page link itself
                            continue
                            
                        if job_url in seen_urls:
                            continue
                            
                        seen_urls.add(job_url)

                        if not self.should_process_job(title):
                            continue

                        job_id = f"{self.site_key}_{hash(job_url)}"
                        
                        job = get_job_dict(
                            job_id=job_id,
                            title=title,
                            company=self.company_name,
                            location="Italy", # Default location for Aeroitalia
                            url=job_url,
                            source_url=self.base_url,
                            description="Aeroitalia Career Opportunity.",
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
