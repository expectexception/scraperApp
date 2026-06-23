"""
Lufthansa Group careers scraper — apply.lufthansagroup.careers
Covers Lufthansa, SWISS, Austrian Airlines, Brussels Airlines via the
Lufthansa Group "beesite" career portal. The site migrated off its old
SuccessFactors domain (career.be-lufthansa.com, now dead/unresolvable);
jobs are now listed via a public sitemap.xml on the new apply portal.
"""

import asyncio
import logging
import re
import requests
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://apply.lufthansagroup.careers"
SITEMAP_URL = f"{BASE_URL}/sitemap.xml"


class LufthansaGroupScraper(BaseScraper):
    """Lufthansa Group careers scraper (LH, SWISS, Austrian, Brussels)."""

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="lufthansa_group", db_manager=db_manager)
        self.company_name = "Lufthansa Group"
        self.base_url = BASE_URL

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Fetching Lufthansa Group careers...")

        try:
            resp = requests.get(
                SITEMAP_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"}
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "xml")
            urls = [loc.get_text(strip=True) for loc in soup.find_all("loc")]
            job_urls = [u for u in urls if "ac=jobad" in u and "id=" in u]
            logger.info(f"[{self.site_key}] Found {len(job_urls)} job ads in sitemap")
        except Exception as e:
            logger.error(f"[{self.site_key}] Failed to fetch sitemap: {e}")
            return jobs

        for url in job_urls:
            if self.max_jobs and len(jobs) >= self.max_jobs:
                break
            match = re.search(r"id=(\d+)", url)
            job_id = match.group(1) if match else url
            jobs.append(
                {
                    "company": self.company_name,
                    "title": "",
                    "location": "Germany",
                    "url": url,
                    "source_url": BASE_URL,
                    "apply_url": url,
                    "job_seq_no": job_id,
                    "is_active": True,
                }
            )

        logger.info(f"[{self.site_key}] Found {len(jobs)} jobs")
        return jobs

    async def _fetch_job_page(self, job, semaphore) -> None:
        async with semaphore:
            try:
                resp = await asyncio.to_thread(
                    requests.get,
                    job["url"],
                    timeout=20,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    h1 = soup.find("h1")
                    if h1:
                        job["title"] = h1.get_text(strip=True)
                    desc = (
                        soup.find("div", class_="jobDescription")
                        or soup.find("div", id="job-details")
                        or soup.find("main")
                    )
                    if desc:
                        job["description"] = desc.get_text(" ", strip=True)[:3000]
            except Exception as e:
                logger.warning(f"[{self.site_key}] Page fetch error for {job['url']}: {e}")

    async def fetch_job_titles(self, jobs) -> list:
        """Titles aren't in the sitemap — fetch each ad page once (concurrently),
        grab title and description together so the later pass can skip pages
        already fetched here."""
        semaphore = asyncio.Semaphore(10)
        await asyncio.gather(*(self._fetch_job_page(job, semaphore) for job in jobs))
        return [j for j in jobs if j.get("title")]

    async def fetch_job_descriptions(self, jobs) -> list:
        semaphore = asyncio.Semaphore(10)
        pending = [j for j in jobs if not j.get("description")]
        await asyncio.gather(*(self._fetch_job_page(j, semaphore) for j in pending))
        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        if not jobs:
            return []
        jobs = await self.fetch_job_titles(jobs)
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
