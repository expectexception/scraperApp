"""
Government of Canada Jobs scraper (canada.ca / GC Jobs).
Uses the public GC Jobs search endpoint with aviation-relevant keywords.
"""

import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://emploisfp-psjobs.cfp-psc.gc.ca"
SEARCH_URL = (
    "https://emploisfp-psjobs.cfp-psc.gc.ca/srs-sre/page01E.htm"
    "?poster=1&toggle=1&simpleSearch=0&freeText={keyword}&action=searchJob"
)
KEYWORDS = [
    "dispatcher",
    "flight operations",
    "air traffic",
    "operations coordinator",
    "aviation",
]


class CanadaGcScraper(BaseScraper):
    """Canada Public Service Commission job board (GC Jobs)."""

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="canada_gc", db_manager=db_manager)
        self.company_name = "Government of Canada"
        self.base_url = BASE_URL

    async def fetch_jobs(self) -> list:
        jobs = []
        seen = set()
        logger.info(f"[{self.site_key}] Searching GC Jobs...")

        for keyword in KEYWORDS:
            if self.max_jobs and len(jobs) >= self.max_jobs:
                break
            try:
                url = SEARCH_URL.format(keyword=requests.utils.quote(keyword))
                resp = requests.get(url, timeout=30, headers={"Accept-Language": "en"})
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                rows = soup.select("table.table-condensed tbody tr")
                logger.info(f"[{self.site_key}] keyword='{keyword}': {len(rows)} rows")

                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) < 4:
                        continue
                    link = cells[0].find("a")
                    if not link:
                        continue
                    title = link.text.strip()
                    href = urljoin(BASE_URL, link.get("href", ""))
                    job_id = str(hash(href))
                    if job_id in seen:
                        continue
                    seen.add(job_id)

                    department = (
                        cells[1].text.strip()
                        if len(cells) > 1
                        else "Government of Canada"
                    )
                    location = cells[2].text.strip() if len(cells) > 2 else "Canada"
                    cells[3].text.strip() if len(cells) > 3 else ""

                    if not location.endswith("Canada"):
                        location = f"{location}, Canada"

                    jobs.append(
                        {
                            "company": department,
                            "title": title,
                            "location": location,
                            "url": href,
                            "source_url": url,
                            "apply_url": href,
                            "job_seq_no": job_id,
                            "is_active": True,
                            "posted_date": None,
                        }
                    )
            except Exception as e:
                logger.error(f"[{self.site_key}] Error for keyword='{keyword}': {e}")
            await asyncio.sleep(1)

        logger.info(f"[{self.site_key}] Total unique jobs: {len(jobs)}")
        return jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        for job in jobs:
            try:
                resp = requests.get(job["url"], timeout=20)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    content = soup.find("div", id="job-description") or soup.find(
                        "main"
                    )
                    if content:
                        job["description"] = content.get_text(" ", strip=True)[:3000]
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
