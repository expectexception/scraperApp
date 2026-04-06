import asyncio
import logging
import re
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class CargojetScraper(BaseScraper):
    """
    Scraper for Cargojet (UltiPro)
    URL: https://recruiting.ultipro.ca/CAR5000CJT/JobBoard/3bdb0a52-04dc-4fa4-91cd-d80afd88843d/
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='cargojet', db_manager=db_manager)
        self.base_url = "https://recruiting.ultipro.ca/CAR5000CJT/JobBoard/3bdb0a52-04dc-4fa4-91cd-d80afd88843d/"
        self.company_name = "Cargojet"

    async def fetch_jobs(self) -> list:
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until='networkidle', timeout=60000)
                
                # Wait for UltiPro content to load
                await page.wait_for_selector('.opportunity', timeout=30000)
                
                page_count = 1
                while True:
                    if self.max_pages and page_count > self.max_pages:
                        break
                        
                    logger.info(f"[{self.site_key}] Processing page {page_count}...")
                    
                    job_rows = await page.query_selector_all('.opportunity')
                    if not job_rows:
                        break

                    logger.info(f"[{self.site_key}] Found {len(job_rows)} job rows on page {page_count}")
                    
                    page_jobs_data = []
                    for row in job_rows:
                        try:
                            title_el = await row.query_selector('a.opportunity-link')
                            if not title_el:
                                continue
                                
                            title = await title_el.inner_text()
                            url_suffix = await title_el.get_attribute('href')
                            # Ensure URL is absolute
                            url = f"https://recruiting.ultipro.ca{url_suffix}" if url_suffix.startswith('/') else url_suffix
                            
                            loc_el = await row.query_selector('[data-automation="city-state-zip-country-label"]')
                            location = await loc_el.inner_text() if loc_el else "Canada"
                            
                            req_el = await row.query_selector('span[data-bind*="RequisitionNumber"]')
                            job_id = await req_el.inner_text() if req_el else str(hash(url))
                            
                            page_jobs_data.append({
                                'title': title.strip(),
                                'url': url,
                                'location': location.strip(),
                                'job_id': job_id.strip()
                            })
                        except Exception as e:
                            logger.error(f"[{self.site_key}] Error parsing row: {e}")
                            continue

                    # Process jobs
                    for job_data in page_jobs_data:
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break
                            
                        if not self.should_process_job(job_data['title']):
                            continue

                        if await self.is_url_already_scraped(job_data['url']):
                            continue

                        try:
                            logger.info(f"[{self.site_key}] Fetching details for: {job_data['url']}")
                            detail_page = await context.new_page()
                            await detail_page.goto(job_data['url'], wait_until='domcontentloaded', timeout=30000)
                            await detail_page.wait_for_timeout(2000)
                            
                            # UltiPro descriptions are in [data-automation="job-description"]
                            desc_el = await detail_page.query_selector('[data-automation="job-description"]')
                            description = ""
                            if desc_el:
                                description = await desc_el.inner_text()
                            else:
                                description = await self.extract_description_from_page(detail_page)
                                
                            job = get_job_dict(
                                job_id=f"cargojet_{job_data['job_id']}",
                                title=job_data['title'],
                                company=self.company_name,
                                location=job_data['location'],
                                url=job_data['url'],
                                source_url=self.base_url,
                                description=description.strip(),
                                apply_url=job_data['url'],
                                posted_date=None,
                                source=self.site_key
                            )
                            
                            jobs.append(job)
                            await detail_page.close()
                            await self.random_delay(1, 3)
                            
                        except Exception as e:
                            logger.error(f"[{self.site_key}] Error fetching job detail ({job_data['url']}): {e}")
                            continue

                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    # UltiPro often uses "Load More" or numeric pagination if there are many jobs
                    # Currently Cargojet has 36 jobs, all on one page
                    load_more = await page.query_selector('button[data-automation="load-more"]')
                    if load_more and await load_more.is_visible():
                        logger.info(f"[{self.site_key}] Clicking Load More...")
                        await load_more.click()
                        await page.wait_for_timeout(5000)
                        page_count += 1
                    else:
                        break
                        
            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
            finally:
                await context.close()
                await browser.close()
                
        return jobs

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
