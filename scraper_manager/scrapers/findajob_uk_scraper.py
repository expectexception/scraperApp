"""
Find a Job UK scraper (findajob.dwp.gov.uk).
Uses the public search API with aviation/dispatch keywords.
"""

import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://findajob.dwp.gov.uk"
SEARCH_URL = "https://findajob.dwp.gov.uk/search"
KEYWORDS = [
    "dispatcher",
    "flight operations",
    "aviation operations",
    "operations controller",
]


class FindajobUkScraper(BaseScraper):
    """UK Government Find a Job portal scraper."""

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="findajob_uk", db_manager=db_manager)
        self.company_name = "Find a Job (UK)"
        self.base_url = BASE_URL

    async def fetch_jobs(self) -> list:
        jobs = []
        seen = set()
        logger.info(f"[{self.site_key}] Searching Find a Job UK...")

        for keyword in KEYWORDS:
            if self.max_jobs and len(jobs) >= self.max_jobs:
                break
            try:
                params = {"q": keyword, "pp": 50}
                resp = requests.get(
                    SEARCH_URL,
                    params=params,
                    timeout=30,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                if resp.status_code != 200:
                    logger.warning(
                        f"[{self.site_key}] HTTP {resp.status_code} for '{keyword}'"
                    )
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                items = soup.select("li.search-result")
                logger.info(
                    f"[{self.site_key}] keyword='{keyword}': {len(items)} results"
                )

                for item in items:
                    link = item.find("a", class_="search-result-job-title")
                    if not link:
                        link = item.find("h3").find("a") if item.find("h3") else None
                    if not link:
                        continue

                    title = link.text.strip()
                    href = urljoin(BASE_URL, link.get("href", ""))
                    job_id = str(hash(href))
                    if job_id in seen:
                        continue
                    seen.add(job_id)

                    employer = item.select_one(".search-result-company")
                    location = item.select_one(".search-result-location")
                    posted = item.select_one("time")

                    jobs.append(
                        {
                            "company": employer.text.strip()
                            if employer
                            else "UK Employer",
                            "title": title,
                            "location": (location.text.strip() + ", United Kingdom")
                            if location
                            else "United Kingdom",
                            "url": href,
                            "source_url": SEARCH_URL,
                            "apply_url": href,
                            "job_seq_no": job_id,
                            "is_active": True,
                            "posted_date": posted.get("datetime", "")[:10]
                            if posted
                            else None,
                        }
                    )
            except Exception as e:
                logger.error(f"[{self.site_key}] Error for '{keyword}': {e}")
            await asyncio.sleep(1)

        logger.info(f"[{self.site_key}] Found {len(jobs)} jobs")
        return jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        for job in jobs:
            try:
                resp = requests.get(
                    job["url"], timeout=20, headers={"User-Agent": "Mozilla/5.0"}
                )
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    desc = soup.find("div", class_="job-description") or soup.find(
                        "main"
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
