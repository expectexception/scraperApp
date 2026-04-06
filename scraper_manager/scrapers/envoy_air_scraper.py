import asyncio
import logging
import re
from datetime import datetime
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class EnvoyAirScraper(BaseScraper):
    """
    Scraper for Envoy Air (iCIMS)
    URL: https://careers-envoyair.icims.com/jobs/search?in_iframe=1
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='envoy_air', db_manager=db_manager)
        self.base_url = "https://careers-envoyair.icims.com/jobs/search?in_iframe=1"
        self.company_name = "Envoy Air"

    async def fetch_jobs(self) -> list:
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until='domcontentloaded', timeout=60000)
                await page.wait_for_timeout(5000)
                
                page_count = 1
                while True:
                    if self.max_pages and page_count > self.max_pages:
                        break
                        
                    logger.info(f"[{self.site_key}] Processing page {page_count}...")
                    
                    # Handle potential iCIMS iframe
                    # Some implementations use a nested iframe, others don't.
                    frame = page
                    iframe_el = await page.query_selector('iframe#icims_bootstrap_frame, iframe')
                    if iframe_el:
                        logger.info(f"[{self.site_key}] Switching context to iCIMS iframe...")
                        frame = page.frame_locator('iframe#icims_bootstrap_frame').first
                        if not await frame.locator('.iCIMS_JobsTable').is_visible(timeout=10000):
                            # Try general iframe if the bootstrap one isn't there
                            frame = page.frame_locator('iframe').first

                    # Ensure results are loaded
                    try:
                        await frame.locator('.iCIMS_JobsTable .row, .iCIMS_JobListing').first.wait_for(timeout=15000)
                    except:
                        logger.warning(f"[{self.site_key}] Timeout waiting for jobs on page {page_count}")
                        break

                    # Extract jobs from the list
                    job_rows = await frame.locator('.iCIMS_JobsTable .row, .iCIMS_JobListing').all()
                    if not job_rows:
                        logger.warning(f"[{self.site_key}] No job rows found on page {page_count}")
                        break

                    logger.info(f"[{self.site_key}] Found {len(job_rows)} job rows on page {page_count}")
                    
                    page_jobs_data = []
                    for row in job_rows:
                        try:
                            # Title and Link
                            title_el = row.locator('div.title a.iCIMS_Anchor, a.iCIMS_JobListingLink').first
                            if not await title_el.is_visible():
                                continue
                                
                            title = await title_el.inner_text()
                            url = await title_el.get_attribute('href')
                            if url and '?' in url:
                                url = url.split('?')[0] # Clean dynamic params
                            if url and not url.startswith('http'):
                                url = "https://careers-envoyair.icims.com" + url
                            
                            # Location - search in header left
                            location = "USA"
                            loc_el = row.locator('.header.left span:not(.sr-only), .location span:nth-child(2)').first
                            if await loc_el.is_visible():
                                location = await loc_el.inner_text()
                            
                            # Requisition ID
                            req_id = ""
                            # Try searching specifically for the ID label/value
                            id_el = row.locator('span:has-text("ID") + span, .iCIMS_JobHeaderGroup dl:has(dt:has-text("ID")) dd').first
                            if await id_el.is_visible():
                                req_id = await id_el.inner_text()
                            else:
                                # Fallback to parsing text or links
                                row_text = await row.inner_text()
                                match = re.search(r'ID\s*(\d+-\d+)', row_text)
                                if match:
                                    req_id = match.group(1)
                            
                            page_jobs_data.append({
                                'title': title.strip(),
                                'url': url,
                                'location': location.strip(),
                                'req_id': req_id.strip()
                            })
                        except Exception as e:
                            logger.debug(f"[{self.site_key}] Skipping row: {e}")
                            continue

                    # Visit each job detail page
                    for job_data in page_jobs_data:
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break
                            
                        url = job_data['url']
                        title = job_data['title']
                        
                        if not self.should_process_job(title):
                            continue

                        if await self.is_url_already_scraped(url):
                            continue

                        try:
                            # Use in_iframe=1 for detail view as well
                            detail_url = url + "?in_iframe=1"
                            logger.info(f"[{self.site_key}] Fetching details for: {detail_url}")
                            detail_page = await context.new_page()
                            await detail_page.goto(detail_url, wait_until='domcontentloaded', timeout=30000)
                            
                            # iCIMS often loads description dynamically
                            try:
                                await detail_page.wait_for_selector('.iCIMS_JobDescription, .iCIMS_JobContents, .iCIMS_InfoTable_JobDescription, .iCIMS_InfoTable', timeout=10000)
                            except:
                                logger.debug(f"[{self.site_key}] Timeout waiting for description selector on detail page.")

                            await detail_page.wait_for_timeout(2000)
                            
                            # iCIMS specific description container
                            icims_desc = await detail_page.query_selector('.iCIMS_JobDescription, .iCIMS_JobContents, .iCIMS_InfoTable_JobDescription, .iCIMS_InfoTable')
                            if icims_desc:
                                description = await icims_desc.inner_text()
                            else:
                                description = await self.extract_description_from_page(detail_page)

                            # Clean up description noise (common iCIMS headers)
                            noise_patterns = [
                                r"Returning Candidate\?.*?Log back in!",
                                r"Welcome page.*?Log back in!",
                                r"Sorry the Share function is not working.*?try again later\.",
                                r"Share on your newsfeed",
                                r"Loading\.\.\.\.\.\."
                            ]
                            for pattern in noise_patterns:
                                description = re.sub(pattern, "", description, flags=re.DOTALL | re.IGNORECASE)
                            
                            description = description.strip()

                            # Extract Requisition ID or use hash
                            job_id = job_data.get('req_id')
                            if not job_id:
                                # Look for it in detail page
                                id_el = await detail_page.query_selector('.iCIMS_JobHeaderTable dl:has(dt:has-text("ID")) dd')
                                if id_el:
                                    job_id = await id_el.inner_text()
                                else:
                                    job_id = f"envoy_{hash(url)}"
                            
                            if not job_id.startswith('envoy_'):
                                job_id = f"envoy_{job_id.strip()}"

                            job = get_job_dict(
                                job_id=job_id,
                                title=title,
                                company=self.company_name,
                                location=job_data['location'],
                                url=url,
                                source_url=self.base_url,
                                description=description,
                                apply_url=url,
                                posted_date=None,
                                source=self.site_key
                            )
                            
                            jobs.append(job)
                            await detail_page.close()
                            await self.random_delay(1, 3)
                            
                        except Exception as e:
                            logger.error(f"[{self.site_key}] Error fetching job detail ({url}): {e}")
                            continue

                    # Pagination
                    try:
                        next_btn = frame.locator('a.glyph[title*="Next page"], a:has(span.sr-only:has-text("Next page"))').first
                        if await next_btn.is_visible() and await next_btn.is_enabled():
                            logger.info(f"[{self.site_key}] Clicking Next button...")
                            await next_btn.click()
                            await page.wait_for_timeout(5000)
                            page_count += 1
                        else:
                            logger.info(f"[{self.site_key}] No more pages found.")
                            break
                    except Exception as e:
                        logger.error(f"[{self.site_key}] Error navigating to next page: {e}")
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
