import logging
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class FlylevelScraper(BaseScraper):
    """
    Scraper for Fly LEVEL using TeamTailor format.
    URL: https://careers.flylevel.com/jobs
    """

    def __init__(self, config: Dict, db_manager=None):
        super().__init__(config, site_key="flylevel", db_manager=db_manager)
        self.base_url = "https://careers.flylevel.com/jobs"
        self.company_name = "Fly LEVEL"

    async def fetch_jobs(self) -> List[Dict]:
        jobs = []
        
        try:
            logger.info(f"[{self.site_key}] Fetching {self.base_url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(self.base_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # TeamTailor usually puts jobs in list items with links containing /jobs/
            job_links = soup.select('a[href*="/jobs/"]')
            logger.info(f"[{self.site_key}] Found {len(job_links)} potential job links")
            
            seen_urls = set()
            for link in job_links:
                href = link.get('href')
                if not href or 'department' in href.lower() or 'location' in href.lower():
                    continue
                    
                # The title is usually inside the link or a span inside it
                title = link.text.strip().split('\n')[0].strip()
                
                # Check inside spans if title is empty
                if not title or len(title) < 3:
                    title_span = link.select_one('span.text-block-base-link, span.font-bold')
                    if title_span:
                        title = title_span.text.strip()
                        
                if not title or len(title) < 3:
                    continue
                    
                job_url = urljoin(self.base_url, href)
                if job_url in seen_urls:
                    continue
                seen_urls.add(job_url)
                
                if not self.should_process_job(title):
                    continue
                    
                location = "Unknown"
                loc_span = link.select_one('div.mt-1 span, span.text-md, .text-gray-500')
                if loc_span:
                    location = loc_span.text.strip()
                    
                job_id = f"{self.site_key}_{hash(job_url)}"
                
                job = get_job_dict(
                    job_id=job_id,
                    title=title,
                    company=self.company_name,
                    location=location,
                    url=job_url,
                    source_url=self.base_url,
                    description="Fly LEVEL Career Opportunity.",
                    apply_url=job_url,
                    source=self.site_key
                )
                
                jobs.append(job)
                
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break
                    
            return jobs
            
        except Exception as e:
            logger.error(f"[{self.site_key}] Error scraping: {e}")
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
