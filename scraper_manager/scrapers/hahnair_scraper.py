import asyncio
import logging
from datetime import datetime
from playwright.async_api import async_playwright
import re

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class HahnAirScraper(BaseScraper):
    """
    Scraper for Hahn Air Lines
    URL: https://www.hahnair.com/en/career/career
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='hahnair', db_manager=db_manager)
        self.base_url = "https://www.hahnair.com/en/career/career"
        self.company_name = "Hahn Air Lines"

    async def fetch_jobs(self) -> list:
        """
        Scrape jobs from Hahn Air Personio XML feed
        """
        jobs = []
        xml_url = "https://hahnair.jobs.personio.de/xml"
        
        try:
            logger.info(f"[{self.site_key}] Fetching jobs from {xml_url}")
            response_obj = await self.make_request(
                method='GET',
                url=xml_url
            )
            
            if not response_obj:
                logger.error(f"[{self.site_key}] Failed to fetch XML feed")
                return jobs
            
            response = response_obj.text
                
            # Basic regex to extract jobs from XML to avoid additional dependencies
            position_pattern = r'<position[^>]*>(.*?)</position>'
            positions = re.findall(position_pattern, response, re.DOTALL)
            
            logger.info(f"[{self.site_key}] Found {len(positions)} jobs in XML")
            
            for i, pos_xml in enumerate(positions):
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break
                    
                # Extract title (handle both CDATA and plain text)
                title_match = re.search(r'<name>(?:<!\[CDATA\[(.*?)\]\]>|(.*?))</name>', pos_xml, re.DOTALL)
                if not title_match:
                    continue
                title = (title_match.group(1) or title_match.group(2) or "").strip()
                if not self.should_scrape_job(title):
                    continue
                
                # Extract job ID
                id_match = re.search(r'<id>(.*?)</id>', pos_xml)
                job_id_str = id_match.group(1).strip() if id_match else f"hahnair_{i+1}"
                job_id = f"hahnair_{job_id_str}"
                
                # Extract description (handle both CDATA and plain text)
                desc = ""
                desc_match = re.search(r'<jobDescriptions>(.*?)</jobDescriptions>', pos_xml, re.DOTALL)
                if desc_match:
                    content = desc_match.group(1).strip()
                    # Remove CDATA wrappers
                    content = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', content, flags=re.DOTALL)
                    # Remove common XML tags inside if they stick
                    content = re.sub(r'<jobDescription>', '', content)
                    content = re.sub(r'</jobDescription>', '\n', content)
                    content = re.sub(r'<name>.*?</name>', '', content, flags=re.DOTALL)
                    content = re.sub(r'<value>(.*?)</value>', r'\1', content, flags=re.DOTALL)
                    desc = content.strip()
                    
                if not desc or len(desc) < 50:
                    desc = "Hahn Air Lines career opportunities. Please visit the official career portal for more details."
                    
                # Extract location (handle both CDATA and plain text)
                loc_match = re.search(r'<office>(?:<!\[CDATA\[(.*?)\]\]>|(.*?))</office>', pos_xml, re.DOTALL)
                location = (loc_match.group(1) or loc_match.group(2) or "Germany").strip() if loc_match else "Germany"
                    
                # Extract URLs (we need to construct the URL for Personio jobs)
                url = f"https://hahnair.jobs.personio.de/job/{job_id_str}"
                
                job = get_job_dict(
                    job_id=job_id,
                    title=title,
                    company=self.company_name,
                    location=location,
                    url=url,
                    source_url=url,
                    description=desc,
                    apply_url=f"{url}#apply",
                    posted_date="", # Personio XML often doesn't have an easily parsed publish date
                    source=self.site_key
                )
                
                jobs.append(job)
                
        except Exception as e:
            logger.error(f"[{self.site_key}] Error parsing XML feed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        jobs = [j for j in jobs if j is not None]
        await self.save_results(jobs)
        return jobs
