import asyncio
import logging
import re
from datetime import datetime
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class JetAviationScraper(BaseScraper):
    """
    Scraper for Jet Aviation.
    Uses Playwright to navigate their SuccessFactors/RMK job board.
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='jet_aviation', db_manager=db_manager)
        self.base_url = "https://jobs.jetaviation.com"
        # The specific search URL provided by the user
        self.search_url = "https://jobs.jetaviation.com/go/Europe/8766702/?q=&q2=&alertId=&title=dispatch&location=&facility=&date=#searchresults"
        self.company_name = "Jet Aviation"

    async def fetch_jobs(self) -> list:
        logger.info(f"[{self.site_key}] Navigating to {self.search_url} (Headless={self.headless})...")
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                # Direct navigation to search results
                await page.goto(self.search_url, wait_until='networkidle', timeout=60000)
                await self.simulate_human_behavior(page)
                
                # Wait for the search results table
                try:
                    await page.wait_for_selector('table#searchresults tr.data-row', timeout=20000)
                except Exception:
                    logger.warning(f"[{self.site_key}] Timeout waiting for job rows. Checking if any jobs are present.")

                # Extract job listings
                job_rows = await page.query_selector_all('table#searchresults tr.data-row')
                logger.info(f"[{self.site_key}] Found {len(job_rows)} potential job rows in listing")
                
                initial_jobs = []
                for row in job_rows:
                    title_elem = await row.query_selector('td.colTitle span.jobTitle a.jobTitle-link')
                    loc_elem = await row.query_selector('td.colLocation span.jobLocation')
                    date_elem = await row.query_selector('td.colDate span.jobDate')
                    
                    if title_elem:
                        title = (await title_elem.inner_text()).strip()
                        href = await title_elem.get_attribute('href')
                        if href and href.startswith('/'):
                            url = self.base_url + href
                        else:
                            url = href
                            
                        location = (await loc_elem.inner_text()).strip() if loc_elem else "Unknown"
                        posted_date_raw = (await date_elem.inner_text()).strip() if date_elem else ""
                        
                        initial_jobs.append({
                            'title': title,
                            'url': url,
                            'location': location,
                            'posted_date_raw': posted_date_raw
                        })

                logger.info(f"[{self.site_key}] {len(initial_jobs)} potential jobs. Applying pre-filter...")
                
                # PRE-FILTER: Filter by title first to skip irrelevant roles
                matched_initial, _, _ = self.apply_title_filter(initial_jobs)
                
                logger.info(f"[{self.site_key}] {len(matched_initial)} jobs passed pre-filtering. Fetching details...")

                for i, j_initial in enumerate(matched_initial):
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                    
                    url = j_initial['url']
                    title = j_initial['title']
                    location = j_initial['location']
                    posted_date_raw = j_initial['posted_date_raw']
                    
                    try:
                        if not self.should_process_job(title):
                            continue

                        if await self.is_url_already_scraped(url):
                            continue

                        logger.info(f"[{self.site_key}] Fetching details for: {url}")
                        detail_page = await context.new_page()
                        await detail_page.goto(url, wait_until='domcontentloaded', timeout=30000)
                        await self.random_delay(1, 2)
                        
                        # Extract description from the specific SuccessFactors detail container
                        desc_elem = await detail_page.query_selector('div.joblayouttoken, div.job')
                        if desc_elem:
                            description = await desc_elem.inner_text()
                        else:
                            # Fallback using base method
                            description = await self.extract_description_from_page(detail_page)
                        
                        # Parse posted date
                        posted_date = ""
                        if posted_date_raw:
                            parsed_date = self.parse_posted_date(posted_date_raw)
                            posted_date = parsed_date if parsed_date else posted_date_raw

                        job_id = f"jetaviation_{re.sub(r'[^a-zA-Z0-9]', '', url)[-10:]}"
                        
                        job = get_job_dict(
                            job_id=job_id,
                            title=title,
                            company=self.company_name,
                            location=location,
                            url=url,
                            source_url=self.search_url,
                            description=description,
                            source=self.site_key,
                            posted_date=posted_date
                        )
                        jobs.append(job)
                        await detail_page.close()
                    except Exception as e:
                        logger.warning(f"[{self.site_key}] Error detail page {url}: {e}")
                        
            except Exception as e:
                logger.error(f"[{self.site_key}] Main page error: {e}")
            finally:
                await context.close()
                await browser.close()
                
        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        
        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
