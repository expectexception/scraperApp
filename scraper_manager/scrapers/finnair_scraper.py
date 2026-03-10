import asyncio
import logging
from datetime import datetime
from playwright.async_api import async_playwright
import re
import json

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class FinnairScraper(BaseScraper):
    """
    Scraper for Finnair
    URL: https://company.finnair.com/en/careers
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='finnair', db_manager=db_manager)
        self.base_url = "https://finnair.wd103.myworkdayjobs.com/wday/cxs/finnair/finnair/jobs"
        self.company_name = "Finnair"

    async def fetch_jobs(self) -> list:
        """
        Scrape jobs from Finnair's Workday ATS
        """
        jobs = []
        payload = {
            "appliedFacets": {},
            "limit": 20,
            "offset": 0,
            "searchText": ""
        }
        
        try:
            from curl_cffi import requests as curl_requests
        except ImportError:
            logger.error(f"[{self.site_key}] curl_cffi not installed, cannot bypass WAF.")
            return jobs
            
        while True:
            try:
                logger.info(f"[{self.site_key}] Fetching jobs from Workday ATS API (offset {payload['offset']})")
                
                # Make POST request to Workday API using curl_cffi to bypass WAF
                response = curl_requests.post(
                    url=self.base_url,
                    json=payload,
                    headers={
                        "Accept": "application/json",
                        "Accept-Language": "en-US",
                        "Content-Type": "application/json",
                        "Origin": "https://finnair.wd103.myworkdayjobs.com",
                        "Referer": "https://finnair.wd103.myworkdayjobs.com/finnair"
                    },
                    impersonate="chrome110",
                    timeout=30
                )
                
                if response.status_code != 200:
                    logger.error(f"[{self.site_key}] Target returned status {response.status_code}")
                    break
                    
                try:
                    data = json.loads(response.text)
                except Exception as e:
                    logger.error(f"[{self.site_key}] JSON parse failed. Body: {response.text[:500]}")
                    break
                if not isinstance(data, dict):
                    logger.error(f"[{self.site_key}] Expected dict but got {type(data)}: {str(data)[:200]}")
                    break
                    
                job_list = data.get('jobPostings', [])
                
                if not job_list:
                    break
                    
                for item in job_list:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    title = item.get('title', '')
                    externalPath = item.get('externalPath', '')
                    url = f"https://finnair.wd103.myworkdayjobs.com/en-US/finnair{externalPath}"
                    
                    location = item.get('locationsText', 'Finland')
                    posted_date = item.get('postedOn', '')
                    
                    # Process jobReqId from bulletFields
                    job_req_id = ""
                    bullet_fields = item.get('bulletFields', [])
                    if bullet_fields:
                        if isinstance(bullet_fields[0], str):
                            job_req_id = bullet_fields[0]
                        elif isinstance(bullet_fields[0], dict):
                            job_req_id = bullet_fields[0].get('jobReqId', '')
                            
                    job_id = f"finnair_{job_req_id}" if job_req_id else f"finnair_{externalPath.split('/')[-1]}"
                    
                    job = get_job_dict(
                        job_id=job_id,
                        title=title,
                        company=self.company_name,
                        location=location,
                        url=url,
                        source_url=url,
                        description="", # To be filled in secondary pass
                        apply_url=url,
                        posted_date=posted_date,
                        source=self.site_key
                    )
                    
                    jobs.append(job)
                    
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break
                    
                # Pagination
                payload['offset'] += payload['limit']
                total = data.get('total', 0)
                if payload['offset'] >= total:
                    break
                    
            except Exception as e:
                import traceback
                logger.error(f"[{self.site_key}] Error fetching jobs from API: {e}\n{traceback.format_exc()}")
                break
                
        # Fetch details for descriptions
        if jobs:
            self.logger.info(f"[{self.site_key}] Fetching descriptions for {len(jobs)} jobs...")
            tasks = [self._fetch_job_description(job) for job in jobs]
            await asyncio.gather(*tasks)
        
        return jobs

    async def _fetch_job_description(self, job):
        """Fetch full job description from Workday detail API"""
        full_url = job.get('url', '')
        # Convert website URL to API URL
        # URL: https://finnair.wd103.myworkdayjobs.com/en-US/finnair/job/Vantaa/Sourcing-Manager_R265750
        # API: https://finnair.wd103.myworkdayjobs.com/wday/cxs/finnair/finnair/job/Vantaa/Sourcing-Manager_R265750
        api_url = full_url.replace("/en-US/finnair", "/wday/cxs/finnair/finnair")
        
        try:
            from curl_cffi import requests as curl_requests
            response = curl_requests.get(
                url=api_url,
                headers={"Accept": "application/json"},
                impersonate="chrome110",
                timeout=20
            )
            if response.status_code == 200:
                data = json.loads(response.text)
                desc = data.get('jobPostingInfo', {}).get('jobDescription', '')
                job['description'] = desc
            else:
                self.logger.warning(f"[{self.site_key}] Failed to fetch description for {job['job_id']} (Status {response.status_code})")
        except Exception as e:
            self.logger.error(f"[{self.site_key}] Error fetching description for {job['job_id']}: {e}")

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        jobs = [j for j in jobs if j is not None]
        await self.save_results(jobs)
        return jobs
