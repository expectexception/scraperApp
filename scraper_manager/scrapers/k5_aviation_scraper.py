import asyncio
import logging
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup
import requests

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class K5AviationScraper(BaseScraper):
    """
    Scraper for K5 Aviation
    URL: https://www.k5-aviation.com/en/k5-inside-en/
    """

    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="k5aviation", db_manager=db_manager)
        self.base_url = "https://www.k5-aviation.com/en/k5-inside-en/"
        self.company_name = "K5 Aviation"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []

        try:
            logger.info(f"[{self.site_key}] Fetching jobs from {self.base_url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            resp = requests.get(self.base_url, headers=headers, timeout=30)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # The jobs are in div.et_pb_toggle_content under the "Jobs" section
            # The title is in h3.et_pb_toggle_title
            
            # Find the Jobs section by ID
            jobs_section = soup.find(id="jobs-en")
            if not jobs_section:
                logger.warning(f"[{self.site_key}] Could not find jobs section")
                return jobs

            toggles = jobs_section.find_all("div", class_="et_pb_toggle")
            
            for toggle in toggles:
                title_tag = toggle.find("h3", class_="et_pb_toggle_title")
                content_tag = toggle.find("div", class_="et_pb_toggle_content")
                
                if not title_tag or not content_tag:
                    continue
                    
                title = title_tag.text.strip()
                description = content_tag.get_text("\n").strip()
                
                if not self.should_process_job(title):
                    continue
                    
                job_id = f"k5_{hash(title)}"
                url = self.base_url + "#jobs"
                
                job = get_job_dict(
                    job_id=job_id,
                    title=title,
                    company=self.company_name,
                    location="Germany", # default from text
                    url=url,
                    source_url=self.base_url,
                    description=description,
                    apply_url="mailto:jobs@k5-group.com",
                    source=self.site_key,
                )
                
                jobs.append(job)

        except Exception as e:
            logger.error(f"[{self.site_key}] Error scraping: {e}")

        return jobs

    async def run(self):
        self.print_header()
        jobs_raw = await self.fetch_jobs()
        jobs = [j for j in jobs_raw if j is not None]
        
        if self.use_filter and self.filter_manager and jobs:
            jobs, _, _ = self.apply_title_filter(jobs)
            
        jobs, _ = await self.filter_new_jobs(jobs)
        await self.save_results(jobs)
        return jobs
