"""
American Airlines careers scraper — jobs.aa.com
Uses the SuccessFactors/Taleo JSON API endpoint.
"""

import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://jobs.aa.com"
SF_API = "https://jobs.aa.com/api/apply/v2/jobs"
KEYWORDS = ["dispatcher", "operations", "flight operations", "OCC", "crew scheduling"]


class AmericanAirlinesScraper(BaseScraper):
    """American Airlines careers (SuccessFactors portal)."""

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="american_airlines", db_manager=db_manager)
        self.company_name = "American Airlines"
        self.base_url = BASE_URL

    async def fetch_jobs(self) -> list:
        jobs = []
        seen = set()
        logger.info(f"[{self.site_key}] Fetching American Airlines careers...")

        for keyword in KEYWORDS:
            if self.max_jobs and len(jobs) >= self.max_jobs:
                break
            try:
                params = {
                    "domain": "aa.com",
                    "start": 0,
                    "num": 25,
                    "keyword": keyword,
                }
                resp = requests.get(
                    SF_API,
                    params=params,
                    timeout=30,
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "Accept": "application/json",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    postings = data.get("jobPostings", [])
                    logger.info(
                        f"[{self.site_key}] keyword='{keyword}': {len(postings)} jobs"
                    )
                    for p in postings:
                        title = p.get("title", "").strip()
                        job_id = str(p.get("jobId", hash(title)))
                        if not title or job_id in seen:
                            continue
                        seen.add(job_id)
                        location = p.get("location", "United States")
                        url = urljoin(
                            BASE_URL, p.get("externalPath", f"/jobs/{job_id}")
                        )
                        jobs.append(
                            {
                                "company": self.company_name,
                                "title": title,
                                "location": location,
                                "url": url,
                                "source_url": BASE_URL,
                                "apply_url": url,
                                "job_seq_no": job_id,
                                "is_active": True,
                                "posted_date": p.get("postedOn", "")[:10] or None,
                            }
                        )
                else:
                    # Fallback HTML scrape
                    search_url = (
                        f"{BASE_URL}/search-jobs/{requests.utils.quote(keyword)}"
                    )
                    r2 = requests.get(
                        search_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}
                    )
                    if r2.status_code == 200:
                        soup = BeautifulSoup(r2.text, "html.parser")
                        for item in soup.select("li.job, div.job-listing, article"):
                            link = item.find("a")
                            if not link:
                                continue
                            t = link.text.strip()
                            href = urljoin(BASE_URL, link.get("href", ""))
                            jid = str(hash(href))
                            if jid in seen:
                                continue
                            seen.add(jid)
                            jobs.append(
                                {
                                    "company": self.company_name,
                                    "title": t,
                                    "location": "United States",
                                    "url": href,
                                    "source_url": BASE_URL,
                                    "apply_url": href,
                                    "job_seq_no": jid,
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
        for job in jobs:
            try:
                resp = requests.get(
                    job["url"], timeout=20, headers={"User-Agent": "Mozilla/5.0"}
                )
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    desc = (
                        soup.find("div", class_="jobDescription")
                        or soup.find("div", id="job-details")
                        or soup.find("main")
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
