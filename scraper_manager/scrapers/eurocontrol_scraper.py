import logging
import asyncio
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class EurocontrolScraper(BaseScraper):
    """
    Scraper for Eurocontrol Careers.
    URL: https://jobs.eurocontrol.int/eurocontrol-vacancies/?date=all&keywords=&sort=alphabetical
    """

    def __init__(self, config: Dict, db_manager=None):
        super().__init__(config, site_key="eurocontrol", db_manager=db_manager)
        self.base_url = "https://jobs.eurocontrol.int/eurocontrol-vacancies/?date=all&keywords=&sort=alphabetical"
        self.company_name = "Eurocontrol"

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
            
            job_links = [a for a in soup.select('a') if a.get('href') and '/jobs/' in a.get('href')]
            logger.info(f"[{self.site_key}] Found {len(job_links)} potential job links")
            
            seen_urls = set()
            for link in job_links:
                href = link.get('href')
                if not href:
                    continue
                    
                title = link.text.strip()
                if not title or len(title) < 3:
                    continue
                    
                job_url = href
                if job_url in seen_urls:
                    continue
                seen_urls.add(job_url)
                
                if not self.should_process_job(title):
                    continue
                    
                job_id = f"{self.site_key}_{hash(job_url)}"
                
                job = get_job_dict(
                    job_id=job_id,
                    title=title,
                    company=self.company_name,
                    location="Europe",
                    url=job_url,
                    source_url=self.base_url,
                    description="Eurocontrol Career Opportunity.",
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
