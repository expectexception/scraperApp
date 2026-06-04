"""
WMD scraper stub — config references WmdScraper but no module exists yet.
Registered as a placeholder to prevent 'no implementation' skip.
Update BASE_URL and parsing logic when the actual WMD portal is identified.
"""

import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

BASE_URL = "https://www.wmd.com/careers"


class WmdScraper(BaseScraper):
    """WMD careers scraper (stub — update URL and selectors when confirmed)."""

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="wmd", db_manager=db_manager)
        self.company_name = "WMD"
        self.base_url = BASE_URL

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Fetching WMD careers...")
        try:
            resp = requests.get(
                BASE_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"}
            )
            if resp.status_code != 200:
                logger.warning(
                    f"[{self.site_key}] HTTP {resp.status_code} — WMD URL may need updating"
                )
                return []
            soup = BeautifulSoup(resp.text, "html.parser")
            for item in soup.select(".job, .vacancy, article, li.position"):
                link = item.find("a")
                if not link:
                    continue
                title = link.text.strip()
                href = urljoin(BASE_URL, link.get("href", ""))
                job_id = str(hash(href))
                job = get_job_dict(
                    job_id=job_id,
                    title=title,
                    company=self.company_name,
                    location="Unknown",
                    url=href,
                    source_url=BASE_URL,
                    description="",
                    apply_url=href,
                    source=self.site_key
                )
                jobs.append(job)
        except Exception as e:
            logger.error(f"[{self.site_key}] Error: {e}")
        logger.info(f"[{self.site_key}] Found {len(jobs)} jobs")
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
