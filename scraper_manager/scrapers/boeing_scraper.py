import asyncio
import random
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from playwright.async_api import async_playwright, Page

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class BoeingScraper(BaseScraper):
    """
    Scraper for Boeing Jobs
    
    Structure:
    - Search page with keyword and location inputs
    - Pagination via "Next" button
    - Job details on separate pages
    - OneTrust cookie banner
    """
    
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key='boeing', db_manager=db_manager)
        self.base_url = "https://jobs.boeing.com"
        self.search_url = f"{self.base_url}/search-jobs"
        
    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Scrape jobs from Boeing
        """
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                # 1. Navigate to search page
                logger.info(f"[{self.site_key}] Navigating to {self.search_url}")
                try:
                    await page.goto(self.search_url, wait_until='networkidle', timeout=60000)
                except Exception as e:
                    logger.warning(f"[{self.site_key}] Initial navigation timeout: {e}")
                
                 # 2. Handle Cookie Banner
                try:
                    accept_btn = await page.wait_for_selector('#onetrust-accept-btn-handler', timeout=10000)
                    if accept_btn:
                        await accept_btn.click()
                        await page.wait_for_selector('#onetrust-banner-sdk', state='hidden', timeout=5000)
                        logger.info(f"[{self.site_key}] Accepted cookies")
                except Exception:
                    logger.info(f"[{self.site_key}] No cookie banner found or already accepted")
                
                # 3. Perform Search (if config has queries/locations)
                site_config = self.config.get('scrapers', {}).get('boeing', {})
                search_queries = site_config.get('search_queries', [])
                search_locations = site_config.get('search_locations', [])
                
                # For simplicity, we'll pick the first query/location combo or just default search if empty
                # Ideally we loop through combinations, but let's do the primary one for now
                if not search_queries:
                    search_queries = [""] # Default empty query
                
                if not search_locations:
                    search_locations = [""] # Default empty location

                # Create search combinations (Query + Location)
                # To avoid explosion, we might want to search queries (global) 
                # OR search locations (global) OR pairs.
                # Common pattern: Loop queries, and optionally set location.
                # If both lists have items, we'll iterate both. (Cartesian product)
                
                search_combinations = []
                for q in search_queries:
                    for l in search_locations:
                        search_combinations.append((q, l))
                        
                for query, loc in search_combinations:
                    if len(jobs) >= self.max_jobs:
                        break
                        
                    logger.info(f"[{self.site_key}] Search: Keyword='{query}', Location='{loc}'")
                    
                    try:
                        # TalentBrew supports direct search URLs which are much more reliable than filling and clicking
                        search_params = f"k={query}&l={loc}"
                        direct_url = f"{self.base_url}/search-jobs?{search_params}"
                        
                        logger.info(f"[{self.site_key}] Loading search results via URL: {direct_url}")
                        await page.goto(direct_url, wait_until='domcontentloaded', timeout=45000)
                        await self.random_delay(2, 4)
                        
                        # Wait for either results list or "no jobs found" message
                        try:
                            await page.wait_for_selector('#search-results-list, .search-results__no-results', timeout=30000)
                        except Exception as e:
                            logger.warning(f"[{self.site_key}] Results did not load: {e}")
                            
                    except Exception as e:
                        logger.warning(f"[{self.site_key}] Search load failed: {e}")
                        continue

                    # 4. Scrape Pages for this combination
                    page_count = 0
                    while len(jobs) < self.max_jobs:
                        logger.info(f"[{self.site_key}] Processing page {page_count + 1} for '{query}' in '{loc}'")
                        
                        # Wait for results
                        try:
                            await page.wait_for_selector('#search-results-list ul li', timeout=10000)
                        except Exception:
                             logger.warning(f"[{self.site_key}] No results found for '{query}' in '{loc}' on page {page_count + 1}")
                             break
                             
                        # Extract jobs from current list
                        job_elements = await page.query_selector_all('#search-results-list ul li')
                        logger.info(f"[{self.site_key}] Found {len(job_elements)} jobs on page")
                        
                        for el in job_elements:
                            if len(jobs) >= self.max_jobs:
                                break
                                
                            try:
                                link = await el.query_selector('a.search-results__job-link')
                                if not link:
                                    continue
                                    
                                title = await link.inner_text()
                                url_suffix = await link.get_attribute('href')
                                job_url = self.base_url + url_suffix if url_suffix.startswith('/') else url_suffix
                                
                                loc_el = await el.query_selector('.search-results__job-info.location')
                                location = await loc_el.inner_text() if loc_el else "Unknown"
                                
                                # Navigate to detail page for description in a new tab
                                detail_page = await context.new_page()
                                try:
                                    await detail_page.goto(job_url, wait_until='domcontentloaded', timeout=30000)
                                    desc_el = await detail_page.query_selector('div.ats-description')
                                    if not desc_el:
                                         desc_el = await detail_page.query_selector('main') 
                                    
                                    description = await desc_el.inner_html() if desc_el else ""
                                    
                                except Exception as e:
                                    logger.warning(f"[{self.site_key}] Failed to load detail {job_url}: {e}")
                                    description = ""
                                finally:
                                    await detail_page.close()
                                    
                                # Build a unique job_id from the URL path
                                import re as _re
                                job_id_match = _re.search(r'/(\d+)(?:[/?]|$)', url_suffix or '')
                                job_id = job_id_match.group(1) if job_id_match else f"boeing_{len(jobs)+1}"

                                job_data = {
                                    'job_id': f"boeing_{job_id}",
                                    'source': self.site_key,          # required for DB source tracking
                                    'company': self.company_name,
                                    'title': title.strip(),
                                    'location': location.strip(),
                                    'url': job_url,
                                    'employment_type': 'Full-time',
                                    'description': description.strip(),
                                    'source_url': job_url,
                                    'apply_url': job_url,
                                    'posted_date': datetime.now().date(),   # must be date, not datetime
                                    'is_active': True
                                }
                                jobs.append(job_data)
                                
                            except Exception as e:
                                logger.error(f"[{self.site_key}] Error parsing job card: {e}")
                        
                        # Pagination within this search
                        if len(jobs) >= self.max_jobs:
                            break

                        next_btn = await page.query_selector('a.next:not(.disabled)')
                        if next_btn:
                            await next_btn.click()
                            await page.wait_for_load_state('networkidle')
                            page_count += 1
                            await asyncio.sleep(random.uniform(2, 4))
                        else:
                            logger.info(f"[{self.site_key}] Reached last page for '{query}' in '{loc}'")
                            break
            
            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
                
        return jobs

    async def run(self):
        """Main entry point for the scraper"""
        self.print_header()
        jobs = await self.fetch_jobs()
        await self.save_results(jobs)
        return jobs
