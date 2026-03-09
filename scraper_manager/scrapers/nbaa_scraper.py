
import asyncio
import logging
import re
from typing import List, Dict, Any
from datetime import datetime
from playwright.async_api import async_playwright, Page

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class NBAAScraper(BaseScraper):
    """
    Scraper for NBAA (National Business Aviation Association)
    """
    
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key='nbaa', db_manager=db_manager)
        self.jobs_url = config.get('jobs_url', "https://jobs.nbaa.org/jobs/")
        self.base_url = config.get('base_url', "https://jobs.nbaa.org")
        
    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                # 1. Navigate to main listing
                logger.info(f"[{self.site_key}] Navigating to {self.jobs_url}")
                await page.goto(self.jobs_url, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(3)
                
                # 2. Extract job links
                # Usually standard rows
                # Look for typical detail links
                
                while len(jobs) < self.max_jobs:
                     # Get all potential job links
                     # Chunk showed links like https://jobs.nbaa.org/jobs/...
                     # Often inside a Result container
                     
                     job_links_set = set()
                     
                     # Debug: log page content snippet
                     # content = await page.content()
                     # logger.info(f"Page content snippet: {content[:500]}")
                     
                     # Try multiple selector patterns for job links
                     # 1. Standard .bti-ui-job-detail-container a (common in this platform)
                     # 2. Generic a with href containing /job/ or /jobs/
                     
                     elements = await page.query_selector_all('a')
                     for el in elements:
                         href = await el.get_attribute('href')
                         if href:
                             # Clean href
                             if href.startswith('/'):
                                 full_url = self.base_url.rstrip('/') + href
                             elif href.startswith('http'):
                                 full_url = href
                             else:
                                 continue
                             
                             # Check for job patterns
                             if '/job/' in full_url or '/jobs/view/' in full_url:
                                 # Exclude non-job pages
                                 if 'search' not in full_url and 'login' not in full_url:
                                     job_links_set.add(full_url)
                                     
                     logger.info(f"[{self.site_key}] Found {len(job_links_set)} jobs on page")
                     
                     # Visit details
                     for url in job_links_set:
                        if len(jobs) >= self.max_jobs:
                            break
                        
                        if await self.is_url_already_scraped(url):
                            continue
                            
                        try:
                            # Visit detailed page
                            detail_page = await context.new_page()
                            await detail_page.goto(url, wait_until='domcontentloaded', timeout=30000)
                            
                            # Extract Details
                            title = "Unknown Title"
                            
                            # Strategy 1: H1
                            title_el = await detail_page.query_selector('h1')
                            if title_el:
                                title = await title_el.inner_text()
                            
                            # Strategy 2: Page Title
                            if title == "Unknown Title":
                                page_title = await detail_page.title()
                                if page_title:
                                    title = page_title.split('|')[0].strip() # Clean content
                                    
                            # Strategy 3: Meta tags
                            if title == "Unknown Title":
                                 meta_title = await detail_page.query_selector('meta[property="og:title"]')
                                 if meta_title:
                                    title = await meta_title.get_attribute('content')
                            
                            logger.info(f"[{self.site_key}] Processing: {title}")
                            
                            description = await self.extract_description_from_page(detail_page)
                            
                            # Location/Company from headers
                            company = "Unknown Company"
                            location = "Unknown"
                            
                            # Try generic search for company in h2 or similar
                            # NBAA structure often: H1 Title, H2 or strong Company
                            
                            # Apply Link
                            apply_url = url
                            apply_btn = await detail_page.query_selector('a:has-text("Apply"), a[class*="apply"]')
                            if apply_btn:
                                href = await apply_btn.get_attribute('href')
                                if href and href.startswith('http'):
                                     apply_url = href

                            job_data = {
                                'company': company,
                                'title': title.strip(),
                                'location': location,
                                'description': description,
                                'source_url': url,
                                'apply_url': apply_url,
                                'url': url,
                                'posted_date': datetime.now().isoformat(),
                                'is_active': True
                            }
                            
                            jobs.append(job_data)
                            await detail_page.close()
                        except Exception as e:
                             logger.error(f"[{self.site_key}] detail error {url}: {e}")
                             if 'detail_page' in locals():
                                await detail_page.close()

                     # Pagination
                     if len(jobs) >= self.max_jobs:
                         break
                         
                     next_el = await page.query_selector('a[aria-label="Next Page"], a[rel="next"], li.next a')
                     if next_el:
                         logger.info(f"[{self.site_key}] Next page...")
                         await next_el.click()
                         await page.wait_for_load_state('domcontentloaded')
                         await asyncio.sleep(3)
                     else:
                         break
                         
            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
                
        return jobs

    async def run(self):
        """Main entry point"""
        self.print_header()
        jobs = await self.fetch_jobs()
        await self.save_results(jobs)
        return jobs
