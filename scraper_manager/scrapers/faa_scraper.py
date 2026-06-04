"""
FAA (Federal Aviation Administration) jobs scraper.
FAA posts on USAJOBS — this scraper uses the USAJOBS API filtered to FAA agency.
"""

import asyncio
import logging
import requests

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

API_URL = "https://data.usajobs.gov/api/search"
HEADERS = {
    "Host": "data.usajobs.gov",
    "User-Agent": "aeroops@example.com",
    "Authorization-Key": "",
}
KEYWORDS = ["dispatcher", "aviation safety", "flight operations", "air traffic", "OCC"]


class FaaScraper(BaseScraper):
    """FAA jobs via USAJOBS API (Organization=FA filter)."""

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="faa", db_manager=db_manager)
        self.company_name = "Federal Aviation Administration"
        self.base_url = "https://www.faa.gov/jobs"

    async def fetch_jobs(self) -> list:
        jobs = []
        seen = set()
        logger.info(f"[{self.site_key}] Fetching FAA job listings...")

        for keyword in KEYWORDS:
            if self.max_jobs and len(jobs) >= self.max_jobs:
                break
            try:
                params = {
                    "Keyword": keyword,
                    "Organization": "FA",  # FAA agency code
                    "ResultsPerPage": 50,
                }
                resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
                if resp.status_code != 200:
                    continue

                data = resp.json()
                items = data.get("SearchResult", {}).get("SearchResultItems", [])
                logger.info(
                    f"[{self.site_key}] keyword='{keyword}': {len(items)} results"
                )

                for item in items:
                    mv = item.get("MatchedObjectDescriptor", {})
                    title = mv.get("PositionTitle", "").strip()
                    job_id = mv.get("PositionID", "")
                    if not title or job_id in seen:
                        continue
                    seen.add(job_id)

                    locations = mv.get("PositionLocation", [])
                    loc = (
                        ", ".join(f"{l.get('CityName', '')}, US" for l in locations)
                        if locations
                        else "United States"
                    )

                    apply_uri = mv.get("ApplyURI", [""])[0]
                    posted = mv.get("PublicationStartDate", "")[:10]
                    jobs.append(
                        {
                            "company": self.company_name,
                            "title": title,
                            "location": loc,
                            "url": f"https://www.usajobs.gov/job/{job_id}",
                            "source_url": self.base_url,
                            "apply_url": apply_uri
                            or f"https://www.usajobs.gov/job/{job_id}",
                            "job_seq_no": job_id,
                            "is_active": True,
                            "posted_date": posted or None,
                        }
                    )
            except Exception as e:
                logger.error(f"[{self.site_key}] Error: {e}")
            await asyncio.sleep(1)

        logger.info(f"[{self.site_key}] Found {len(jobs)} jobs")
        return jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        return jobs  # USAJOBS detail is text-heavy; skip for now

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        if not jobs:
            return []
        if self.use_filter and self.filter_manager:
            jobs, _, stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(stats)
            if not jobs:
                return []
        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []
        jobs = await self.fetch_job_descriptions(jobs)
        await self.save_results(jobs)
        return jobs
