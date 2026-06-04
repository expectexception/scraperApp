"""
GovernmentJobs.com (NEOGOV) scraper.
Targets US municipal/state aviation & dispatch postings via public search API.
"""

import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.governmentjobs.com"
API_URL = "https://www.governmentjobs.com/careers/search"
KEYWORDS = [
    "dispatcher",
    "aviation",
    "airport operations",
    "flight operations",
    "emergency dispatcher",
]


class GovernmentjobsScraper(BaseScraper):
    """GovernmentJobs.com (NEOGOV) portal for US public sector aviation jobs."""

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="governmentjobs", db_manager=db_manager)
        self.company_name = "GovernmentJobs"
        self.base_url = BASE_URL

    async def fetch_jobs(self) -> list:
        jobs = []
        seen = set()
        logger.info(f"[{self.site_key}] Searching GovernmentJobs...")

        for keyword in KEYWORDS:
            if self.max_jobs and len(jobs) >= self.max_jobs:
                break
            try:
                params = {
                    "keyword": keyword,
                    "sortField": "Date",
                    "sortOrder": "Descending",
                }
                resp = requests.get(
                    f"{BASE_URL}/careers/search",
                    params=params,
                    timeout=30,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                if resp.status_code != 200:
                    # Try JSON API
                    api_resp = requests.get(
                        f"{BASE_URL}/api/agencyjobs/search",
                        params={"keyword": keyword, "limit": 50},
                        timeout=30,
                        headers={
                            "Accept": "application/json",
                            "User-Agent": "Mozilla/5.0",
                        },
                    )
                    if api_resp.status_code == 200:
                        try:
                            data = api_resp.json()
                            for item in data.get("data", []):
                                title = item.get("title", "").strip()
                                job_id = str(item.get("id", hash(title)))
                                if not title or job_id in seen:
                                    continue
                                seen.add(job_id)
                                location = f"{item.get('city', '')}, {item.get('state', '')}, USA".strip(
                                    ", "
                                )
                                url = urljoin(
                                    BASE_URL, item.get("url", f"/careers/{job_id}")
                                )
                                jobs.append(
                                    {
                                        "company": item.get(
                                            "agencyName", "Government Agency"
                                        ),
                                        "title": title,
                                        "location": location or "United States",
                                        "url": url,
                                        "source_url": BASE_URL,
                                        "apply_url": url,
                                        "job_seq_no": job_id,
                                        "is_active": True,
                                        "posted_date": item.get("datePosted", "")[:10]
                                        or None,
                                    }
                                )
                        except Exception:
                            pass
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                items = soup.select(".job-result, .job-listing, tr.job-row")
                logger.info(f"[{self.site_key}] keyword='{keyword}': {len(items)} rows")

                for item in items:
                    link = item.find("a", class_="job-title") or item.find("a")
                    if not link:
                        continue
                    title = link.text.strip()
                    href = urljoin(BASE_URL, link.get("href", ""))
                    job_id = str(hash(href))
                    if job_id in seen:
                        continue
                    seen.add(job_id)
                    agency = item.select_one(".agency-name, .employer")
                    location = item.select_one(".location, .city")
                    jobs.append(
                        {
                            "company": agency.text.strip()
                            if agency
                            else "Government Agency",
                            "title": title,
                            "location": (location.text.strip() + ", USA")
                            if location
                            else "United States",
                            "url": href,
                            "source_url": BASE_URL,
                            "apply_url": href,
                            "job_seq_no": job_id,
                            "is_active": True,
                            "posted_date": None,
                        }
                    )
            except Exception as e:
                logger.error(f"[{self.site_key}] Error for '{keyword}': {e}")
            await asyncio.sleep(1)

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
