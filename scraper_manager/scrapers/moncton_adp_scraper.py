import logging
import re
from datetime import datetime
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class MonctonAdpScraper(BaseScraper):
    """Scraper for Aviation Company (Moncton ADP)"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="moncton_adp", db_manager=db_manager)
        self.site_config = config.get("sites", {}).get("moncton_adp", {})
        self.base_url = "https://workforcenow.adp.com"
        self.api_url = "https://workforcenow.adp.com/mascsr/default/careercenter/public/events/staffing/v1/job-requisitions?cid=06351502-0666-4c6f-9a0b-165c5faeab35&ccId=9200784035909_2&lang=en_CA"
        self.detail_api_base = "https://workforcenow.adp.com/mascsr/default/careercenter/public/events/staffing/v1/job-requisitions"
        self.company_name = "Moncton Aviation (ADP)"

    async def fetch_jobs(self) -> list:
        jobs = []
        try:
            logger.info(f"[{self.site_key}] Fetching from ADP API: {self.api_url}")
            response = await self.make_request(self.api_url)
            
            data = response.json()
            requisitions = data.get("jobRequisitions", [])
            
            for req in requisitions:
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break
                    
                item_id = req.get("itemID")
                title = req.get("requisitionTitle")
                if not item_id or not title:
                    continue
                    
                location = "Unknown"
                locations = req.get("requisitionLocations", [])
                if locations and isinstance(locations, list):
                    loc_parts = []
                    address = locations[0].get("address", {})
                    if address.get("cityName"): loc_parts.append(address.get("cityName"))
                    sub = address.get("countrySubdivisionLevel1", {})
                    if sub.get("codeValue"): loc_parts.append(sub.get("codeValue"))
                    if loc_parts:
                        location = ", ".join(loc_parts)
                
                post_date = req.get("postDate", datetime.now().isoformat())
                
                job_url = f"https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid=06351502-0666-4c6f-9a0b-165c5faeab35&ccId=9200784035909_2&lang=en_CA&jobId={item_id}"
                
                job_id = f"moncton_adp_{abs(hash(item_id)) % 10000000}"
                
                jobs.append({
                    "job_id": job_id,
                    "title": title,
                    "company": self.company_name,
                    "source": self.site_key,
                    "url": job_url,
                    "apply_url": job_url,
                    "location": location,
                    "timestamp": post_date,
                    "description": "",
                    "raw_id": item_id
                })
                
        except Exception as e:
            logger.error(f"[{self.site_key}] Error fetching from ADP API: {e}")
            
        return jobs

    async def fetch_job_descriptions(self, jobs: list) -> list:
        if not jobs:
            return jobs
            
        logger.info(f"[{self.site_key}] Fetching descriptions for {len(jobs)} jobs...")
        
        for job in jobs:
            try:
                item_id = job.get("raw_id")
                if not item_id: continue
                
                detail_url = f"{self.detail_api_base}/{item_id}?cid=06351502-0666-4c6f-9a0b-165c5faeab35&ccId=9200784035909_2&lang=en_CA"
                response = await self.make_request(detail_url)
                data = response.json()
                
                html_desc = data.get("requisitionDescription", "")
                if html_desc:
                    soup = BeautifulSoup(html_desc, "html.parser")
                    job["description"] = soup.get_text(separator="\\n", strip=True)
                    
            except Exception as e:
                logger.warning(f"[{self.site_key}] Failed to fetch description for {job['url']}: {e}")
                
        return jobs

    async def run(self):
        self.print_header()
        jobs_raw = await self.fetch_jobs()
        jobs = [get_job_dict(**job) for job in jobs_raw]
        
        if not jobs:
            return []
            
        if self.use_filter and self.filter_manager:
            jobs, _, _ = self.apply_title_filter(jobs)
            if not jobs:
                return []
                
        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []
            
        jobs = await self.fetch_job_descriptions(jobs)
        await self.save_results(jobs)
        return jobs
