"""
NCS India (National Career Service) scraper — ncs.gov.in
Uses the public job search API/HTML for aviation-relevant roles.
"""

import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.ncs.gov.in"
SEARCH_URL = "https://www.ncs.gov.in/Pages/SearchJobs.aspx"
KEYWORDS = [
    "dispatcher",
    "aviation",
    "flight operations",
    "airport operations",
    "air traffic",
]


class NcsIndiaScraper(BaseScraper):
    """National Career Service India portal scraper."""

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="ncs_india", db_manager=db_manager)
        self.company_name = "NCS India"
        self.base_url = BASE_URL

    async def fetch_jobs(self) -> list:
        jobs = []
        seen = set()
        logger.info(f"[{self.site_key}] Searching NCS India...")

        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0"})

        for keyword in KEYWORDS:
            if self.max_jobs and len(jobs) >= self.max_jobs:
                break
            try:
                # NCS has a REST-ish API endpoint
                api = f"{BASE_URL}/api/JobSearch/SearchJobs"
                payload = {
                    "keywords": keyword,
                    "location": "",
                    "pageNo": 1,
                    "pageSize": 25,
                }
                resp = session.post(api, json=payload, timeout=30)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        items = data.get(
                            "jobList", data.get("jobs", data.get("data", []))
                        )
                        logger.info(
                            f"[{self.site_key}] keyword='{keyword}': {len(items)} results"
                        )
                        for item in items:
                            title = item.get("jobTitle", item.get("title", "")).strip()
                            job_id = str(item.get("jobId", item.get("id", hash(title))))
                            if not title or job_id in seen:
                                continue
                            seen.add(job_id)
                            location = item.get("location", item.get("city", "India"))
                            if not str(location).endswith("India"):
                                location = f"{location}, India"
                            employer = item.get(
                                "employerName", item.get("company", "Indian Employer")
                            )
                            url = f"{BASE_URL}/jobdetail/{job_id}"
                            jobs.append(
                                {
                                    "company": employer,
                                    "title": title,
                                    "location": location,
                                    "url": url,
                                    "source_url": BASE_URL,
                                    "apply_url": url,
                                    "job_seq_no": job_id,
                                    "is_active": True,
                                    "posted_date": item.get("postedDate", "")[:10]
                                    or None,
                                }
                            )
                        continue
                    except Exception:
                        pass

                # Fallback: HTML search
                resp2 = session.get(
                    f"{SEARCH_URL}?q={requests.utils.quote(keyword)}", timeout=30
                )
                if resp2.status_code == 200:
                    soup = BeautifulSoup(resp2.text, "html.parser")
                    for item in soup.select(".job-card, .job-listing, .search-result"):
                        link = item.find("a")
                        if not link:
                            continue
                        title = link.text.strip()
                        href = urljoin(BASE_URL, link.get("href", ""))
                        jid = str(hash(href))
                        if jid in seen:
                            continue
                        seen.add(jid)
                        loc_elem = item.select_one(".location")
                        jobs.append(
                            {
                                "company": "Indian Employer",
                                "title": title,
                                "location": (loc_elem.text.strip() + ", India")
                                if loc_elem
                                else "India",
                                "url": href,
                                "source_url": SEARCH_URL,
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
