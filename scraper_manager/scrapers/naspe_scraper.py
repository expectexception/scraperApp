"""
NASPE (National Association of State Personnel Executives) job board scraper.
Maps to state government career portals for dispatch/aviation roles.
"""

import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.naspe.net"
JOBS_URL = "https://www.naspe.net/careers"


class NaspeScraper(BaseScraper):
    """NASPE careers page scraper."""

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="naspe", db_manager=db_manager)
        self.company_name = "NASPE"
        self.base_url = BASE_URL

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Fetching NASPE careers...")

        try:
            resp = requests.get(
                JOBS_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"}
            )
            if resp.status_code != 200:
                logger.warning(f"[{self.site_key}] HTTP {resp.status_code}")
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            # NASPE uses various listing formats
            for item in soup.select(
                ".job-listing, article.job, .career-item, li.posting"
            ):
                link = item.find("a")
                if not link:
                    continue
                title = link.text.strip()
                href = urljoin(BASE_URL, link.get("href", ""))
                job_id = str(hash(href))
                location_elem = item.select_one(".location, .city, .state")
                org_elem = item.select_one(".organization, .agency, .employer")
                jobs.append(
                    {
                        "company": org_elem.text.strip()
                        if org_elem
                        else self.company_name,
                        "title": title,
                        "location": (location_elem.text.strip() + ", USA")
                        if location_elem
                        else "United States",
                        "url": href,
                        "source_url": JOBS_URL,
                        "apply_url": href,
                        "job_seq_no": job_id,
                        "is_active": True,
                        "posted_date": None,
                    }
                )
            logger.info(f"[{self.site_key}] Found {len(jobs)} jobs")
        except Exception as e:
            logger.error(f"[{self.site_key}] Error: {e}")

        return jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        for job in jobs:
            try:
                resp = requests.get(
                    job["url"], timeout=20, headers={"User-Agent": "Mozilla/5.0"}
                )
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    desc = (
                        soup.find("main")
                        or soup.find("article")
                        or soup.find("div", class_="content")
                    )
                    if desc:
                        job["description"] = desc.get_text(" ", strip=True)[:3000]
            except Exception as e:
                logger.warning(f"[{self.site_key}] Desc error: {e}")
            await asyncio.sleep(0.5)
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
        jobs = await self.fetch_job_descriptions(jobs)
        await self.save_results(jobs)
        return jobs
