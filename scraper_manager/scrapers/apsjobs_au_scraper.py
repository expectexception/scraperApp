"""
APS Jobs (Australia) scraper — apsjobs.gov.au
Uses the public JSON API with aviation/dispatch search keywords.
"""

import asyncio
import logging
import requests
from urllib.parse import urljoin

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.apsjobs.gov.au"
API_URL = "https://www.apsjobs.gov.au/s/global-search/{keyword}"
KEYWORDS = ["dispatcher", "aviation", "flight operations", "operations coordinator"]


class ApsjobsAuScraper(BaseScraper):
    """Australian Public Service jobs portal scraper."""

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="apsjobs_au", db_manager=db_manager)
        self.company_name = "APS Jobs (Australia)"
        self.base_url = BASE_URL

    async def fetch_jobs(self) -> list:
        from bs4 import BeautifulSoup

        jobs = []
        seen = set()
        logger.info(f"[{self.site_key}] Searching APS Jobs Australia...")

        for keyword in KEYWORDS:
            if self.max_jobs and len(jobs) >= self.max_jobs:
                break
            try:
                search_url = (
                    f"{BASE_URL}/s/global-search/{requests.utils.quote(keyword)}"
                )
                resp = requests.get(
                    search_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}
                )
                if resp.status_code != 200:
                    # Fallback: try JSON API
                    api = f"{BASE_URL}/s/jobs?q={requests.utils.quote(keyword)}&page=1&pageSize=25"
                    resp = requests.get(
                        api, timeout=30, headers={"Accept": "application/json"}
                    )
                    if resp.status_code != 200:
                        continue
                    try:
                        data = resp.json()
                        items = data.get("jobs", data.get("results", []))
                        for item in items:
                            title = item.get("title", "").strip()
                            href = item.get("url", item.get("applyUrl", ""))
                            job_id = str(item.get("id", hash(href)))
                            if job_id in seen or not title:
                                continue
                            seen.add(job_id)
                            jobs.append(
                                {
                                    "company": item.get(
                                        "agency", "Australian Government"
                                    ),
                                    "title": title,
                                    "location": item.get("location", "Australia")
                                    + ", Australia",
                                    "url": urljoin(BASE_URL, href),
                                    "source_url": BASE_URL,
                                    "apply_url": urljoin(BASE_URL, href),
                                    "job_seq_no": job_id,
                                    "is_active": True,
                                    "posted_date": item.get("openDate", "")[:10]
                                    or None,
                                }
                            )
                        continue
                    except Exception:
                        continue

                soup = BeautifulSoup(resp.text, "html.parser")
                results = soup.select(".job-result, .search-result, article.job")
                logger.info(
                    f"[{self.site_key}] keyword='{keyword}': {len(results)} results"
                )

                for item in results:
                    link = item.find("a")
                    if not link:
                        continue
                    title = link.text.strip()
                    href = urljoin(BASE_URL, link.get("href", ""))
                    job_id = str(hash(href))
                    if job_id in seen or not title:
                        continue
                    seen.add(job_id)

                    agency = item.select_one(".agency, .employer, .department")
                    location = item.select_one(".location, .city")

                    jobs.append(
                        {
                            "company": agency.text.strip()
                            if agency
                            else "Australian Government",
                            "title": title,
                            "location": (location.text.strip() + ", Australia")
                            if location
                            else "Australia",
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
        from bs4 import BeautifulSoup

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
