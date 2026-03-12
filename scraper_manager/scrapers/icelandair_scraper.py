import asyncio
import logging
import re
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class IcelandairScraper(BaseScraper):
    """
    Scraper for Icelandair.
    Uses 50skills JSON API for robust data extraction.
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='icelandair', db_manager=db_manager)
        self.base_url = "https://jobs.50skills.com/icelandair/en"
        self.api_url = "https://static-jobs-api.50skills.app/public/icelandair/jobs.json"
        self.company_name = "Icelandair"

    async def fetch_jobs(self) -> list:
        logger.info(f"[{self.site_key}] Fetching jobs from JSON API: {self.api_url}")
        jobs = []
        
        try:
            response = await self.make_request(self.api_url)
            if response.status_code != 200:
                logger.error(f"[{self.site_key}] Failed to fetch JSON API: {response.status_code}")
                return []
            
            data = response.json()
            logger.info(f"[{self.site_key}] Found {len(data)} items in JSON API")
            
            for item in data:
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break
                
                try:
                    job_url = item.get('url')
                    job_id = f"{self.site_key}_{item.get('id')}"
                    
                    # Try to find English content
                    languages = item.get('languages', [])
                    en_content = next((lang for lang in languages if lang.get('language') == 'en'), None)
                    # Fallback to first language if English not found
                    content = en_content or (languages[0] if languages else {})
                    
                    title = content.get('title', 'Unknown Title')
                    # Prefer full description, then short description
                    description = content.get('description') or content.get('shortDescription') or "No description provided."
                    location = content.get('location') or item.get('locationName') or "Various"
                    
                    # Clean HTML tags from description if present
                    if description and '<' in description and '>' in description:
                        description = re.sub(r'<[^>]+>', '', description).strip()
                    
                    posted_date_raw = item.get('publishedAt') or item.get('createdAt')
                    
                    if not self.should_process_job(title):
                        continue
                    
                    if await self.is_url_already_scraped(job_url):
                        continue
                    
                    job = get_job_dict(
                        job_id=job_id,
                        title=title,
                        company=self.company_name,
                        location=location,
                        url=job_url,
                        source_url=self.base_url,
                        description=description,
                        source=self.site_key,
                        posted_date=self.parse_posted_date(posted_date_raw) if posted_date_raw else None
                    )
                    jobs.append(job)
                except Exception as e:
                    logger.warning(f"[{self.site_key}] Error parsing job item: {e}")
                    
        except Exception as e:
            logger.error(f"[{self.site_key}] Error fetching jobs: {e}", exc_info=True)
            
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
