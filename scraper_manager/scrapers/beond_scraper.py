import asyncio
import logging
import requests
import re
from .base_scraper import BaseScraper
from .job_schema import get_job_dict
from datetime import datetime

logger = logging.getLogger(__name__)

class BeondScraper(BaseScraper):
    """
    Scraper for Beond Airlines (Workable)
    URL: https://apply.workable.com/beond/
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="beond", db_manager=db_manager)
        self.base_url = "https://apply.workable.com/beond/"
        self.api_url = "https://apply.workable.com/api/v3/accounts/beond/jobs"
        self.company_name = "Beond"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(
            f"[{self.site_key}] Querying Workable API directly for Beond jobs..."
        )

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        payload = {
            "query": "",
            "location": [],
            "department": [],
            "worktype": [],
            "remote": [],
        }

        try:
            resp = requests.post(
                self.api_url, json=payload, headers=headers, timeout=20
            )
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", [])
            logger.info(f"[{self.site_key}] API returned {len(results)} jobs")

            for j in results:
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break

                title = j.get("title", "Unknown")
                shortcode = j.get("shortcode", "")
                if not shortcode:
                    continue

                url = f"https://apply.workable.com/beond/j/{shortcode}/"

                # Extract location
                loc_dict = j.get("location", {})
                loc_str = "Unknown"
                if loc_dict:
                    city = loc_dict.get("city", "")
                    country = loc_dict.get("countryName", "") or loc_dict.get("country", "")
                    loc_parts = [p for p in [city, country] if p]
                    if loc_parts:
                        loc_str = ", ".join(loc_parts)

                posted_date_raw = j.get("published", "")
                posted_date = self.parse_posted_date(posted_date_raw) if posted_date_raw else ""

                jobs.append(
                    {
                        "company": self.company_name,
                        "title": title,
                        "location": self.normalize_location(loc_str),
                        "url": url,
                        "source_url": self.base_url,
                        "apply_url": url,
                        "is_active": True,
                        "job_id": f"beond_{shortcode}",
                        "shortcode": shortcode,
                        "posted_date": posted_date,
                        "timestamp": datetime.now().isoformat(),
                        "description": "",
                    }
                )
        except Exception as e:
            logger.error(f"[{self.site_key}] Error fetching jobs via API: {e}")

        return jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        if not jobs:
            return []

        logger.info(
            f"[{self.site_key}] Fetching descriptions for {len(jobs)} matched jobs via API..."
        )

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }

        for job in jobs:
            shortcode = job.pop("shortcode", None)
            if not shortcode:
                continue

            try:
                detail_url = f"https://apply.workable.com/api/v2/accounts/beond/jobs/{shortcode}"
                resp = requests.get(detail_url, headers=headers, timeout=20)
                if resp.status_code == 200:
                    data = resp.json()
                    
                    parts = []
                    for section in ["description", "requirements", "benefits"]:
                        val = data.get(section, "")
                        if val:
                            clean_val = re.sub(r"<[^>]+>", " ", val)
                            clean_val = re.sub(r"\s+", " ", clean_val).strip()
                            if clean_val:
                                parts.append(f"{section.capitalize()}:\n{clean_val}")
                                
                    job["description"] = "\n\n".join(parts)
            except Exception as e:
                logger.warning(
                    f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}"
                )

            await asyncio.sleep(0.5)

        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        if not jobs:
            return []

        if self.use_filter and self.filter_manager:
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)
            if not jobs:
                return []

        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []

        jobs = await self.fetch_job_descriptions(jobs)
        jobs = [get_job_dict(**job) for job in jobs]
        await self.save_results(jobs)
        return jobs
