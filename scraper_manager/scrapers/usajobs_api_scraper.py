"""
USAJOBS Developer API scraper — queries via the official REST API with auth key.
Falls back to public endpoint if no API key configured.
"""

import asyncio
import logging
import requests

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

API_URL = "https://data.usajobs.gov/api/search"
KEYWORDS = [
    "aircraft dispatcher",
    "flight dispatcher",
    "airline dispatcher",
    "operations controller",
    "OCC operator",
    "network operations center",
]


class UsajobsApiScraper(BaseScraper):
    """
    USAJOBS via developer API — targeted aviation dispatch keywords.
    Set USAJOBS_API_KEY env var for higher rate limits.
    """

    def __init__(self, config, db_manager=None):
        import os

        super().__init__(config, site_key="usajobs_api", db_manager=db_manager)
        self.company_name = "USAJOBS (API)"
        self.base_url = "https://data.usajobs.gov"
        self.api_key = os.environ.get("USAJOBS_API_KEY", "")
        self.user_agent = os.environ.get("USAJOBS_USER_AGENT", "aeroops@example.com")

    @property
    def _headers(self):
        return {
            "Host": "data.usajobs.gov",
            "User-Agent": self.user_agent,
            "Authorization-Key": self.api_key,
        }

    async def fetch_jobs(self) -> list:
        jobs = []
        seen = set()
        logger.info(
            f"[{self.site_key}] Querying USAJOBS API for aviation dispatch roles..."
        )

        for keyword in KEYWORDS:
            if self.max_jobs and len(jobs) >= self.max_jobs:
                break
            try:
                params = {
                    "Keyword": keyword,
                    "ResultsPerPage": 50,
                    "SortField": "OpenDate",
                    "SortDirection": "Desc",
                }
                resp = requests.get(
                    API_URL, params=params, headers=self._headers, timeout=30
                )
                if resp.status_code != 200:
                    logger.warning(
                        f"[{self.site_key}] HTTP {resp.status_code} for '{keyword}'"
                    )
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
                        ", ".join(
                            f"{l.get('CityName', '')}, {l.get('CountryCode', 'US')}"
                            for l in locations
                        )
                        if locations
                        else "United States"
                    )

                    apply_uri = mv.get("ApplyURI", [""])[0]
                    posted = mv.get("PublicationStartDate", "")[:10]
                    salary_info = mv.get("PositionRemuneration", [{}])[0]
                    salary = (
                        f"${salary_info.get('MinimumRange', '')}"
                        if salary_info.get("MinimumRange")
                        else ""
                    )

                    jobs.append(
                        {
                            "company": mv.get("OrganizationName", "US Government"),
                            "title": title,
                            "location": loc,
                            "url": f"https://www.usajobs.gov/job/{job_id}",
                            "source_url": API_URL,
                            "apply_url": apply_uri,
                            "job_seq_no": job_id,
                            "is_active": True,
                            "posted_date": posted or None,
                            "salary": salary,
                        }
                    )
            except Exception as e:
                logger.error(f"[{self.site_key}] Error for '{keyword}': {e}")
            await asyncio.sleep(1)

        logger.info(f"[{self.site_key}] Found {len(jobs)} unique aviation jobs")
        return jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        return jobs

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
        await self.save_results(jobs)
        return jobs
