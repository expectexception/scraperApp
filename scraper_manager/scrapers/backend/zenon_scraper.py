import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class ZenonScraper(BaseScraper):
    """
    Scraper for Zenon Aviation Recruitment
    URL: https://www.zenon.aero/candidates/
    """
    
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key='zenon', db_manager=db_manager)
        self.base_url = "https://www.zenon.aero"
        self.jobs_url = "https://www.zenon.aero/candidates/"
        
    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Scrape jobs from Zenon candidates page
        """
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser, 1920, 1080)
            
            try:
                logger.info(f"[{self.site_key}] navigating to {self.jobs_url}")
                await page.goto(self.jobs_url, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(5) # Wait for dynamic content
                await self.simulate_human_behavior(page)
                
                # Based on analysis, job titles are in H3 tags
                # Structure:
                # <h3><a href="...">Title</a></h3>
                # Text node or element: "Location: ..."
                
                job_elements = await page.query_selector_all('h3 a[href*="/job/"]')
                logger.info(f"[{self.site_key}] Found {len(job_elements)} job title headers")
                
                processed_urls = set()
                
                for el in job_elements:
                    if len(jobs) >= self.max_jobs:
                        break
                        
                    url = await el.get_attribute('href')
                    if not url:
                        continue
                        
                    # Normalize URL
                    full_url = url if url.startswith('http') else f"{self.base_url}{url}"
                    
                    if full_url in processed_urls:
                        continue
                        
                    processed_urls.add(full_url)
                    
                    # Extract title
                    title = await el.text_content()
                    title = title.strip() if title else ""
                    
                    logger.info(f"[{self.site_key}] Processing: {title}")
                    
                    # Extract Location
                    # It's usually in the element immediately following the H3
                    location = "Unknown"
                    try:
                        # Get text content of the next sibling of the H3 (parent of a)
                        # We use evaluate to traverse DOM
                        loc_text = await el.evaluate("""(element) => {
                            let parent = element.parentElement; // h3
                            let sibling = parent.nextSibling;
                            while(sibling && sibling.nodeType !== 1 && sibling.nodeType !== 3) {
                                sibling = sibling.nextSibling;
                            }
                            if (sibling) {
                                return sibling.textContent;
                            }
                            return "";
                        }""")
                        
                        if loc_text and "Location:" in loc_text:
                            location = loc_text.replace("Location:", "").strip()
                    except Exception as e:
                        logger.warning(f"[{self.site_key}] Failed to extract location for {title}: {e}")

                    job = {
                        'company': 'Zenon Aviation',
                        'title': title,
                        'location': location,
                        'source_url': full_url,
                        'url': full_url,
                        'apply_url': full_url,
                        'posted_date': None,
                        'is_active': True,
                        'description': ''
                    }
                    
                    jobs.append(job)
                
                # Now fetch details for each job
                logger.info(f"[{self.site_key}] Fetching details for {len(jobs)} jobs...")
                
                for i, job in enumerate(jobs):
                    try:
                        logger.debug(f"[{self.site_key}] Fetching {job['source_url']}")
                        await page.goto(job['source_url'], wait_until='domcontentloaded', timeout=30000)
                        
                        # Extract Description
                        desc = await self.extract_description_from_page(page)
                        job['description'] = desc
                        
                        # Extract Posted Date
                        date = await self.extract_posted_date_from_page(page)
                        if date:
                            job['posted_date'] = date
                        else:
                            job['posted_date'] = None
                            
                        await self.random_delay(1, 3)
                        
                    except Exception as e:
                        logger.error(f"[{self.site_key}] Error processing details for {job['title']}: {e}")
                    
                # Pagination: The user asked to "auto procide to nexpage"
                # But our analysis showed no next page button for jobs.
                # If we did find one, we would click it and loop.
                # For now, we assume single page.
                
            except Exception as e:
                logger.error(f"[{self.site_key}] Error scraping: {e}", exc_info=True)
            finally:
                await browser.close()
                
        return jobs

    async def run(self):
        """Main entry point"""
        self.print_header()
        jobs = await self.fetch_jobs()
        
        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
