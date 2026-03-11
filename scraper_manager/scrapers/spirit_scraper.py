import asyncio
import logging
import json
from typing import List, Dict, Optional
import requests
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class SpiritScraper(BaseScraper):
    """Scraper for Spirit Airlines careers site using their internal JSON API."""
    
    def __init__(self, config: Dict, db_manager=None):
        super().__init__(config, site_key='spirit', db_manager=db_manager)
        self.api_url = "https://careers.spirit.com/api/jobs"
        self.base_url = "https://careers.spirit.com/careers-home/jobs"

    async def fetch_jobs(self) -> List[Dict]:
        """Fetch and parse jobs directly from the JSON API."""
        jobs = []
        page = 1
        max_pages = self.max_pages or 10  # Default to 10 pages if not specified
        
        try:
            while page <= max_pages:
                params = {
                    'page': page,
                    'sortBy': 'relevance',
                    'descending': 'false',
                    'internal': 'false',
                    'domain': 'spirit.jibeapply.com'
                }
                
                logger.info(f"[{self.site_key}] Fetching page {page} from API...")
                
                def fetch_api():
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Referer': self.base_url,
                        'Accept': 'application/json'
                    }
                    return requests.get(self.api_url, params=params, headers=headers, timeout=30.0)
                
                response = await asyncio.to_thread(fetch_api)
                
                if response.status_code != 200:
                    logger.error(f"[{self.site_key}] API returned status {response.status_code}")
                    break
                    
                data = response.json()
                api_jobs = data.get('jobs', [])
                
                if not api_jobs:
                    logger.info(f"[{self.site_key}] No more jobs found on page {page}")
                    break
                    
                logger.info(f"[{self.site_key}] Found {len(api_jobs)} jobs on page {page}")
                
                for job_item in api_jobs:
                    job_data = job_item.get('data', {})
                    title = job_data.get('title', '').strip()
                    req_id = job_data.get('req_id', job_data.get('slug', ''))
                    
                    if not title or not req_id:
                        continue
                        
                    # Early filtering by title
                    if not self.should_process_job(title):
                        continue
                        
                    # Duplicate check
                    job_url = f"{self.base_url}/{req_id}"
                    if await self.is_url_already_scraped(job_url):
                        continue
                        
                    # Extract details
                    description_html = job_data.get('description', job_data.get('responsibilities', ''))
                    location = job_data.get('full_location', job_data.get('short_location', 'Unknown'))
                    
                    jobs.append({
                        'title': title,
                        'company': 'Spirit Airlines',
                        'location': location,
                        'url': job_url,
                        'description': description_html,
                    })
                    
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        logger.info(f"[{self.site_key}] Reached max jobs limit ({self.max_jobs})")
                        return jobs
                
                page += 1
                
            logger.info(f"[{self.site_key}] Successfully parsed {len(jobs)} jobs from API.")
            return jobs
            
        except Exception as e:
            logger.error(f"[{self.site_key}] Error during API fetching: {e}")
            return jobs

    async def run(self):
        """Standard run flow for API-based scraper."""
        self.print_header()
        
        jobs = await self.fetch_jobs()
        
        # Apply strict title filtering against our advanced manager
        matched_jobs, rejected_jobs, stats = self.apply_title_filter(jobs)
        
        # save_results in BaseScraper handles DB persisting
        await self.save_results(matched_jobs)
        
        return matched_jobs
