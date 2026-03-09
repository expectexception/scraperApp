import asyncio
import random
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class EmiratesScraper(BaseScraper):
    """
    Scraper for Emirates Group Careers
    
    Structure:
    - Single page application loading all jobs
    - Detail pages accessible via ID
    - OneTrust cookie banner
    """
    
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key='emirates', db_manager=db_manager)
        self.base_url = "https://www.emiratesgroupcareers.com"
        self.search_url = f"{self.base_url}/search-and-apply/#all"
        
    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Scrape jobs from Emirates Group Careers
        """
        jobs = []
        
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                # 1. Navigate to main list
                logger.info(f"[{self.site_key}] Navigating to {self.search_url}")
                try:
                    # Use domcontentloaded + explicit wait for SPA
                    await page.goto(self.search_url, wait_until='domcontentloaded', timeout=60000)
                    await page.wait_for_timeout(5000) # Explicit wait for SPA init
                except Exception as e:
                    logger.warning(f"[{self.site_key}] Initial navigation timeout/error: {e}")
                
                 # 2. Handle Cookie Banner
                try:
                    accept_btn = await page.wait_for_selector('#onetrust-accept-btn-handler', timeout=10000)
                    if accept_btn:
                        await accept_btn.click()
                        await page.wait_for_selector('#onetrust-banner-sdk', state='hidden', timeout=5000)
                        logger.info(f"[{self.site_key}] Accepted cookies")
                except Exception:
                    logger.info(f"[{self.site_key}] No cookie banner found or already accepted")

                await asyncio.sleep(self.page_load_delay)
                
                # 3. Wait for and extract job cards
                logger.info(f"[{self.site_key}] Waiting for job cards...")
                try:
                    await page.wait_for_selector('section.job-card', timeout=30000)
                except Exception as e:
                    logger.error(f"[{self.site_key}] Failed to load job cards: {e}")
                    return []
                
                # Get all job IDs and basic info from the list
                job_elements = await page.query_selector_all('section.job-card')
                logger.info(f"[{self.site_key}] Found {len(job_elements)} jobs on the list")
                
                potential_jobs = []
                for el in job_elements:
                    job_id = await el.get_attribute('id')
                    # Update selector based on inspection: h4.job-title
                    title_el = await el.query_selector('h4.job-title')
                    if not title_el:
                         title_el = await el.query_selector('.job-card__title')
                         
                    title = await title_el.text_content() if title_el else "Unknown"
                    title = title.strip()
                    
                    # Filter by search queries
                    is_match = False
                    search_queries = self.config.get('scrapers', {}).get('emirates', {}).get('search_queries', [])
                    if not search_queries:
                        is_match = True # no filter
                    else:
                        for query in search_queries:
                            if query.lower() in title.lower():
                                is_match = True
                                break
                    
                    if is_match and job_id:
                        potential_jobs.append({
                            'id': job_id,
                            'title': title
                        })
                
                logger.info(f"[{self.site_key}] Filtered down to {len(potential_jobs)} potential jobs matching queries")
                
                # 4. Visit detail pages for filtered jobs
                for job_meta in potential_jobs[:self.max_jobs]:
                    job_id = job_meta['id']
                    detail_url = f"{self.base_url}/search-and-apply/{job_id}"
                    
                    try:
                        job_data = await self._scrape_job_detail(page, detail_url, job_meta)
                        if job_data:
                            jobs.append(job_data)
                                
                        await asyncio.sleep(random.uniform(self.request_delay_min, self.request_delay_max))
                        
                    except Exception as e:
                        logger.error(f"[{self.site_key}] Error processing job {job_id}: {e}")
            
            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
                
        return jobs

    async def _scrape_job_detail(self, page: Page, url: str, meta: Dict) -> Optional[Dict]:
        """
        Scrape details from a specific job page
        """
        logger.info(f"[{self.site_key}] Scraping detail: {url}")
        try:
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Re-handle cookie if it appears again (sometimes stateless)
            # Usually strictness prevents this, but good safety
            
            # Extract Data
            # Title
            title_el = await page.query_selector('h4.job-title')
            title = await title_el.text_content() if title_el else meta['title']
            
            # Location
            loc_el = await page.query_selector('h6.location')
            location = await loc_el.text_content() if loc_el else "UAE"

            # Closing Date
            closing_date = None
            closing_el = await page.query_selector('h6:has-text("Closing date")')
            if closing_el:
                closing_text = await closing_el.text_content()
                if "Closing date:" in closing_text:
                    closing_date = closing_text.replace("Closing date:", "").strip()
            
            # Description
            desc_el = await page.query_selector('div.job-details-text')
            description = await desc_el.inner_html() if desc_el else ""
            
            # Apply URL
            apply_el = await page.query_selector('a.apply-btn')
            apply_url = await apply_el.get_attribute('href') if apply_el else url
            if apply_url and apply_url.startswith('/'):
                 apply_url = self.base_url + apply_url
            
            # Parse Date if available (often in the list view, but let's check detail text or assume current)
            # The list view had '.job-card__date' -> "Closing date: 31 Mar 2026"
            # We didn't capture it in the list loop above, could improve that later used meta.
            posted_date = datetime.now().isoformat() # Default
            
            job_data = {
                'company': self.company_name,
                'title': title.strip(),
                'location': location.strip(),
                'employment_type': 'Full-time', # Default assumption
                'description': description.strip(),
                'url': url,
                'source_url': url,
                'apply_url': apply_url,
                'posted_date': posted_date,
                'closing_date': closing_date,
                'job_id': meta.get('id'),
                'is_active': True
            }
            
            logger.info(f"[{self.site_key}] Found job: {title}")
            return job_data

        except Exception as e:
            logger.warning(f"[{self.site_key}] Failed to scrape {url}: {e}")
            return None

    async def run(self):
        """Main entry point for the scraper"""
        self.print_header()
        jobs = await self.fetch_jobs()
        await self.save_results(jobs)
        return jobs
