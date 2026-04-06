import asyncio
import logging
import re
import random
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class FlexjetScraper(BaseScraper):
    """
    Scraper for Flexjet (Phenom People)
    URL: https://careers.flexjet.com/us/en/search-results
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='flexjet', db_manager=db_manager)
        self.base_url = "https://careers.flexjet.com/us/en/search-results"
        self.company_name = "Flexjet"

    async def fetch_jobs(self) -> list:
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until='networkidle', timeout=60000)
                
                # Handle cookie consent if visible
                try:
                    await page.click('#consent_prompt_submit, .cookie-consent-button', timeout=5000)
                    logger.info(f"[{self.site_key}] Clicked cookie consent.")
                except:
                    pass

                page_count = 1
                while True:
                    if self.max_pages and page_count > self.max_pages:
                        break
                        
                    logger.info(f"[{self.site_key}] Processing page {page_count}...")
                    
                    # Wait for job row selector
                    try:
                        await page.wait_for_selector('.jobs-list-item', timeout=15000)
                    except:
                        logger.warning(f"[{self.site_key}] No jobs found on page {page_count}")
                        break

                    job_rows = await page.query_selector_all('.jobs-list-item')
                    if not job_rows:
                        break

                    logger.info(f"[{self.site_key}] Found {len(job_rows)} job rows on page {page_count}")
                    
                    page_jobs_data = []
                    for row in job_rows:
                        try:
                            title_el = await row.query_selector('a[data-ph-at-id="job-link"]')
                            if not title_el:
                                continue
                                
                            title = await title_el.inner_text()
                            url = await title_el.get_attribute('href')
                            job_id = await title_el.get_attribute('data-ph-at-job-id-text')
                            
                            loc_el = await row.query_selector('.job-location')
                            location = await loc_el.inner_text() if loc_el else "USA"
                            
                            page_jobs_data.append({
                                'title': title.strip(),
                                'url': url,
                                'location': location.strip(),
                                'job_id': job_id
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
                            
                            # Phenom People descriptions are usually in .job-description or .content
                            desc_el = await detail_page.query_selector('.job-description, .jd-info, .content')
                            description = ""
                            if desc_el:
                                description = await desc_el.inner_text()
                            else:
                                description = await self.extract_description_from_page(detail_page)
                                
                            job = get_job_dict(
                                job_id=f"flexjet_{job_data['job_id']}",
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
                        
                    # Pagination (Phenom People uses "Load More" or numeric)
                    # For Flexjet, it's often a "Load More" button or infinite scroll
                    load_more = await page.query_selector('a[data-ph-at-id="load-more-text"]')
                    if load_more:
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
