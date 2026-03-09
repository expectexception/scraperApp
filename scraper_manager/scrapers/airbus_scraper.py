import asyncio
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from playwright.async_api import async_playwright, Page

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class AirbusScraper(BaseScraper):
    """
    Scraper for Airbus Jobs (Workday)
    
    Uses Internal Workday API:
    POST https://ag.wd3.myworkdayjobs.com/wday/cxs/ag/Airbus/jobs
    """
    
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key='airbus', db_manager=db_manager)
        self.base_url = "https://ag.wd3.myworkdayjobs.com/Airbus"
        self.api_url = "https://ag.wd3.myworkdayjobs.com/wday/cxs/ag/Airbus/jobs"
        
    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Scrape jobs from Airbus Workday API
        """
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            # Create a context to handle cookies/session
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            try:
                # 1. Initialize Session (Workday requires a valid session sometimes)
                logger.info(f"[{self.site_key}] Initializing session...")
                page = await context.new_page()
                try:
                    await page.goto(self.base_url, wait_until='networkidle', timeout=60000)
                except Exception:
                    logger.warning(f"[{self.site_key}] Initial navigation timed out, continuing anyway")
                
                # 2. Prepare Config Parameters
                site_config = self.config.get('scrapers', {}).get('airbus', {})
                search_queries = site_config.get('search_queries', [])
                
                # Default query if none provided
                if not search_queries:
                    search_queries = [""]
                
                for query in search_queries:
                    if len(jobs) >= self.max_jobs:
                        break
                        
                    logger.info(f"[{self.site_key}] Searching for: {query}")
                    
                    offset = 0
                    limit = 20
                    
                    while len(jobs) < self.max_jobs:
                        payload = {
                            "appliedFacets": {},
                            "limit": limit,
                            "offset": offset,
                            "searchText": query
                        }
                        
                        try:
                            # Use page.request to make the API call with browser session
                            response = await page.request.post(
                                self.api_url, 
                                data=payload,
                                headers={
                                    "Content-Type": "application/json",
                                    "Accept": "application/json"
                                }
                            )
                            
                            if response.status != 200:
                                logger.error(f"[{self.site_key}] API Error {response.status}: {response.status_text}")
                                break
                                
                            data = await response.json()
                            job_items = data.get('jobPostings', [])
                            
                            if not job_items:
                                logger.info(f"[{self.site_key}] No more jobs found for query '{query}'")
                                break
                                
                            logger.info(f"[{self.site_key}] Found {len(job_items)} jobs (Offset: {offset})")
                            
                            for item in job_items:
                                if len(jobs) >= self.max_jobs:
                                    break
                                    
                                job_id = item.get('bulletinId')
                                external_path = item.get('externalPath')
                                if not job_id and external_path:
                                    job_id = external_path.split('/')[-1]
                                    
                                title = item.get('title') or "Unknown Title"
                                posted_on = item.get('postedOn')
                                location = item.get('locationsText')
                                
                                # Corrected URL construction: use the domain as base
                                base_domain = "https://ag.wd3.myworkdayjobs.com"
                                full_url = f"{base_domain}{external_path}"
                                
                                # Basic fields from API
                                job = {
                                    'company': self.company_name,
                                    'title': title,
                                    'location': location,
                                    'url': full_url,
                                    'source_url': full_url,
                                    'apply_url': full_url,
                                    'posted_date': posted_on, # Raw string like "Posted 2 Days Ago"
                                    'is_active': True,
                                    'description': '', # Will fetch if needed or leave empty
                                    'job_id': job_id
                                }
                                
                                # Should we fetch description? 
                                # It requires another API call: /wday/cxs/ag/Airbus/job/{bulletinId}
                                # Let's do it for completeness as Workday API is fast.
                                try:
                                    if job_id:
                                        desc_url = f"https://ag.wd3.myworkdayjobs.com/wday/cxs/ag/Airbus/job/{job_id}"
                                        desc_resp = await page.request.get(desc_url)
                                        if desc_resp.status == 200:
                                            desc_data = await desc_resp.json()
                                            desc_info = desc_data.get('jobPostingInfo', {})
                                            job['description'] = desc_info.get('jobDescription')
                                            job['posted_date'] = desc_info.get('postedOn') or job['posted_date']
                                            job['start_date'] = desc_info.get('startDate')
                                            job['employment_type'] = desc_info.get('timeType')
                                            job['job_category'] = desc_info.get('jobCategory')
                                except Exception as e:
                                    logger.warning(f"[{self.site_key}] Failed to fetch description for {job_id}: {e}")
                                
                                jobs.append(job)
                            
                            offset += limit
                            await asyncio.sleep(0.5) # Politeness
                            
                        except Exception as e:
                            logger.error(f"[{self.site_key}] Error fetching offset {offset}: {e}")
                            break
                            
            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
            finally:
                await browser.close()
                
        return jobs

    async def run(self):
        """Main entry point for the scraper"""
        self.print_header()
        jobs = await self.fetch_jobs()
        # Filter out any None values that might have crept in
        jobs = [j for j in jobs if j is not None]
        await self.save_results(jobs)
        return jobs
