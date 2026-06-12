import logging
from bs4 import BeautifulSoup
from datetime import datetime
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class GlockScraper(BaseScraper):
    """Scraper for Glock Aviation & Corporate"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="glock", db_manager=db_manager)
        self.site_config = config.get("sites", {}).get("glock", {})
        self.base_url = "https://jobs.glock.at"
        self.jobs_url = "https://jobs.glock.at/programme/onlinebewerbung_uebersicht.php"
        self.company_name = "Glock"

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
                if "onlinebewerbung_detail.php" not in href:
                    continue
                    
                text_parts = link.get_text(separator="\\n", strip=True).split("\\n")
                if not text_parts or len(text_parts[0]) < 3:
                    continue
                    
                title = text_parts[0].strip()
                if "Initiativ" in title: # Skip unsolicited applications
                    continue
                    
                location = text_parts[1].strip() if len(text_parts) > 1 else "Austria"
                
                job_url = href if href.startswith("http") else self.base_url.rstrip("/") + "/programme/" + href.lstrip("/")
                job_url = job_url.replace("/programme//programme/", "/programme/")
                
                job_id = f"glock_{abs(hash(job_url)) % 10000000}"
                
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
                
                # The description is usually in a div or table, we'll extract the main body
                desc_div = soup.find("div", class_="stellenangebot") or soup.find("div", id="content") or soup.find("body")
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
