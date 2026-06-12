import logging
from bs4 import BeautifulSoup
from datetime import datetime
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class AeroGuardScraper(BaseScraper):
    """Scraper for AeroGuard Flight Training Center (Paycor)"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="aeroguard", db_manager=db_manager)
        self.site_config = config.get("sites", {}).get("aeroguard", {})
        self.base_url = "https://recruitingbypaycor.com"
        self.jobs_url = "https://recruitingbypaycor.com/career/CareerHome.action?clientId=8a7883d088e0b78e0189415b377122db"
        self.company_name = "AeroGuard Flight Training Center"

    async def fetch_jobs(self) -> list:
        jobs = []
        try:
            logger.info(f"[{self.site_key}] Fetching jobs from {self.jobs_url}")
            response = await self.make_request(self.jobs_url)
            soup = BeautifulSoup(response.text, "html.parser")
            
            job_links = soup.find_all("a", href=True)
            for link in job_links:
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break
                    
                href = link['href']
                if "JobIntroduction.action" not in href:
                    continue
                    
                title = link.get_text(strip=True)
                if not title or title.lower() in ["apply", "read more"]:
                    continue
                    
                job_url = href if href.startswith("http") else self.base_url.rstrip("/") + "/" + href.lstrip("/")
                
                # Try to extract location from surrounding elements if possible
                location = "Unknown"
                # Paycor usually stores location in the next div or span
                parent_td = link.find_parent("div", class_="job-title") or link.find_parent("td")
                if parent_td:
                    loc_div = parent_td.find_next_sibling("td")
                    if loc_div:
                        location = loc_div.get_text(strip=True)
                
                job_id = f"aeroguard_{abs(hash(job_url)) % 10000000}"
                
                jobs.append({
                    "job_id": job_id,
                    "title": title,
                    "company": self.company_name,
                    "source": self.site_key,
                    "url": job_url,
                    "apply_url": job_url,
                    "location": location,
                    "timestamp": datetime.now().isoformat(),
                    "description": ""
                })
                
        except Exception as e:
            logger.error(f"[{self.site_key}] Error fetching jobs: {e}")
            
        return jobs

    async def fetch_job_descriptions(self, jobs: list) -> list:
        if not jobs:
            return jobs
            
        logger.info(f"[{self.site_key}] Fetching descriptions for {len(jobs)} jobs...")
        
        for job in jobs:
            try:
                response = await self.make_request(job["url"])
                soup = BeautifulSoup(response.text, "html.parser")
                
                desc_div = soup.find("div", class_="job-description") or soup.find("div", id="jobDescriptionText") or soup.find("form", id="frmJobApply")
                if desc_div:
                    job["description"] = desc_div.get_text(separator="\\n", strip=True)
                else:
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
