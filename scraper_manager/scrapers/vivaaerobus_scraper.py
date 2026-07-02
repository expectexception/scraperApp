import asyncio
import logging
import requests
import re
from datetime import datetime
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class VivaAerobusScraper(BaseScraper):
    """
    Scraper for Viva Aerobus
    URL: https://jobs.vivaaerobus.com/en/departments/operaciones
    API Feed: https://jobs.vivaaerobus.com/jobs.json
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="vivaaerobus", db_manager=db_manager)
        self.site_config = config.get("sites", {}).get("vivaaerobus", {})
        self.base_url = self.site_config.get("base_url", "https://jobs.vivaaerobus.com")
        self.jobs_url = self.site_config.get("jobs_url", "https://jobs.vivaaerobus.com/jobs.json")
        self.company_name = "Viva Aerobus"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Querying Teamtailor JSON Feed: {self.jobs_url}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }

        try:
            # We can use our standard make_request or requests.get
            # Since make_request is async and handles retry/cookies, let's use it!
            # Or use requests for simpler API feeds. Let's use requests for speed/safety.
            resp = requests.get(self.jobs_url, headers=headers, timeout=20)
            resp.raise_for_status()
            data = resp.json()

            items = data.get("items", [])
            logger.info(f"[{self.site_key}] API returned {len(items)} jobs")

            for item in items:
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break

                job_id_raw = item.get("id", "")
                if not job_id_raw:
                    continue
                job_id = f"vivaaerobus_{job_id_raw}"

                title = item.get("title", "").strip()
                url = item.get("url", "")

                posted_date_raw = item.get("date_published", "")
                posted_date = self.parse_posted_date(posted_date_raw) if posted_date_raw else ""

                # Extract location from _jobposting
                job_posting = item.get("_jobposting", {})
                loc_list = []
                for loc in job_posting.get("jobLocation", []):
                    addr = loc.get("address", {})
                    locality = addr.get("addressLocality", "")
                    country = addr.get("addressCountry", "")
                    region = addr.get("addressRegion", "")
                    parts = [p for p in [locality, region, country] if p]
                    if parts:
                        loc_list.append(", ".join(parts))
                location = " / ".join(loc_list) if loc_list else "Unknown"

                # Extract description
                desc_html = job_posting.get("description", "") or item.get("content_html", "")
                desc = re.sub(r"<[^>]+>", " ", desc_html)
                desc = re.sub(r"\s+", " ", desc).strip()

                jobs.append({
                    "job_id": job_id,
                    "title": title,
                    "company": self.company_name,
                    "source": self.site_key,
                    "url": url,
                    "apply_url": url,
                    "location": self.normalize_location(location),
                    "posted_date": posted_date,
                    "timestamp": datetime.now().isoformat(),
                    "description": desc
                })

        except Exception as e:
            logger.error(f"[{self.site_key}] Error fetching jobs: {e}")

        return jobs

    async def fetch_job_descriptions(self, jobs: list) -> list:
        # Descriptions are already fetched in fetch_jobs!
        return jobs

    async def run(self):
        self.print_header()
        jobs_raw = await self.fetch_jobs()
        
        if not jobs_raw:
            return []

        if self.use_filter and self.filter_manager:
            jobs, _, _ = self.apply_title_filter(jobs_raw)
            if not jobs:
                return []
        else:
            jobs = jobs_raw

        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []

        jobs = [get_job_dict(**job) for job in jobs]
        await self.save_results(jobs)
        self.print_sample(jobs)
        return jobs
