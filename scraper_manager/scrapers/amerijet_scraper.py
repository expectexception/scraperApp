import asyncio
import logging
import re
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class AmerijetScraper(BaseScraper):
    """
    Scraper for Amerijet (ADP Workforce Now)
    URL: https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid=b84c1100-8ca6-49d3-8a35-f06ad8084d26&ccId=19000101_000001&lang=en_US
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='amerijet', db_manager=db_manager)
        self.base_url = "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid=b84c1100-8ca6-49d3-8a35-f06ad8084d26&ccId=19000101_000001&lang=en_US"
        self.company_name = "Amerijet"

    async def fetch_jobs(self) -> list:
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until='networkidle', timeout=60000)
                
                # Wait for ADP content to load
                await page.wait_for_selector('.current-openings-details', timeout=30000)
                
                # Scroll to load all jobs if necessary
                await self.auto_scroll(page)
                
                job_rows = await page.query_selector_all('.current-openings-details')
                if not job_rows:
                    logger.warning(f"[{self.site_key}] No job rows found.")
                    return []

                logger.info(f"[{self.site_key}] Found {len(job_rows)} job rows.")
                
                page_jobs_data = []
                for row in job_rows:
                    try:
                        # ADP uses custom sdf-link for titles
                        title_el = await row.query_selector('sdf-link')
                        if not title_el:
                            title_el = await row.query_selector('.current-opening-title') # Fallback
                            
                        if not title_el:
                            continue
                            
                        title = await title_el.inner_text()
                        
                        # ADP uses custom elements and clicks for navigation
                        # We need the jobId to construct a direct link or click
                        # Often the jobId is in the row's data attributes or we can click it
                        
                        loc_el = await row.query_selector('.current-opening-location-item')
                        location = await loc_el.inner_text() if loc_el else "Miami, FL"
                        
                        page_jobs_data.append({
                            'title': title.strip(),
                            'location': location.strip(),
                            'row_el': row
                        })
                    except Exception as e:
                        logger.error(f"[{self.site_key}] Error parsing row: {e}")
                        continue

                # Process jobs
                for i, job_data in enumerate(page_jobs_data):
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    if not self.should_process_job(job_data['title']):
                        continue

                    try:
                        logger.info(f"[{self.site_key}] Fetching details for: {job_data['title']}")
                        
                        # Click the job row to open details
                        rows = await page.query_selector_all('.current-openings-details')
                        if i < len(rows):
                            # Click the sdf-link or the title container
                            title_btn = await rows[i].query_selector('sdf-link')
                            if not title_btn:
                                title_btn = await rows[i].query_selector('.current-opening-title')
                                
                            if title_btn:
                                await title_btn.click()
                                await page.wait_for_timeout(3000)
                                
                                # Wait for description or req ID
                                # Selectors identified: .job-description-requisition, .job-description-data-item
                                try:
                                    await page.wait_for_selector('.job-description-requisition, .job-description-data-item', timeout=15000)
                                except:
                                    logger.warning(f"[{self.site_key}] Timeout waiting for details for {job_data['title']}")
                                
                                # Get Req ID
                                req_el = await page.query_selector('.job-description-requisition')
                                req_text = await req_el.inner_text() if req_el else ""
                                job_id = re.search(r'(\d+)', req_text).group(1) if re.search(r'(\d+)', req_text) else str(hash(job_data['title']))
                                
                                # Get Description
                                desc_el = await page.query_selector('.job-description-data-item')
                                description = await desc_el.inner_text() if desc_el else ""
                                
                                # URL is typically the base URL + jobId in the hash or params
                                # For Amerijet/ADP, we can use the base URL as the job URL if we can't get a direct one
                                current_url = page.url
                                
                                job = get_job_dict(
                                    job_id=f"amerijet_{job_id}",
                                    title=job_data['title'],
                                    company=self.company_name,
                                    location=job_data['location'],
                                    url=current_url,
                                    source_url=self.base_url,
                                    description=description.strip(),
                                    apply_url=current_url,
                                    posted_date=None,
                                    source=self.site_key
                                )
                                
                                jobs.append(job)
                                
                                # Go back to list
                                back_btn = await page.query_selector('button[aria-label="Back to Search Results"], .back-to-search-results')
                                if back_btn:
                                    await back_btn.click()
                                    await page.wait_for_timeout(2000)
                                else:
                                    # Fallback: re-navigate if back button not found
                                    await page.goto(self.base_url, wait_until='networkidle', timeout=60000)
                                    await page.wait_for_selector('.current-openings-details', timeout=15000)
                                
                                await self.random_delay(1, 2)
                                
                    except Exception as e:
                        logger.error(f"[{self.site_key}] Error fetching job detail for {job_data['title']}: {e}")
                        # If error, try to go back or reload
                        await page.goto(self.base_url, wait_until='networkidle', timeout=60000)
                        await page.wait_for_selector('.current-openings-details', timeout=15000)
                        continue

            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
            finally:
                await context.close()
                await browser.close()
                
        return jobs

    async def auto_scroll(self, page):
        """Scroll down to trigger any lazy loading"""
        await page.evaluate("""
            async () => {
                await new Promise((resolve) => {
                    let totalHeight = 0;
                    let distance = 100;
                    let timer = setInterval(() => {
                        let scrollHeight = document.body.scrollHeight;
                        window.scrollBy(0, distance);
                        totalHeight += distance;
                        if(totalHeight >= scrollHeight){
                            clearInterval(timer);
                            resolve();
                        }
                    }, 100);
                });
            }
        """)

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
