"""
UK Civil Aviation Authority careers scraper — careers.caa.co.uk
Uses the SmartRecruiters-based job board.
"""

import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://careers.caa.co.uk"
# SmartRecruiters JSON API
SR_API = "https://api.smartrecruiters.com/v1/companies/UKCAA/postings"


class CaaUkScraper(BaseScraper):
    """UK Civil Aviation Authority career portal."""

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="caa_uk", db_manager=db_manager)
        self.company_name = "UK Civil Aviation Authority"
        self.base_url = BASE_URL

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Fetching CAA UK careers...")

        try:
            resp = requests.get(
                SR_API,
                timeout=30,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                postings = data.get("content", [])
                logger.info(f"[{self.site_key}] Found {len(postings)} postings")
                for p in postings:
                    job_id = str(p.get("id", ""))
                    title = p.get("name", "").strip()
                    location = p.get("location", {})
                    loc_str = ", ".join(
                        filter(
                            None,
                            [
                                location.get("city", ""),
                                location.get("country", "United Kingdom"),
                            ],
                        )
                    )
                    url = f"{BASE_URL}/job/{job_id}"
                    jobs.append(
                        {
                            "company": self.company_name,
                            "title": title,
                            "location": loc_str or "United Kingdom",
                            "url": url,
                            "source_url": BASE_URL,
                            "apply_url": url,
                            "job_seq_no": job_id,
                            "is_active": p.get("jobAd", {}).get("sections", {}) != {},
                            "posted_date": p.get("releasedDate", "")[:10] or None,
                        }
                    )
            else:
                # Fallback: scrape HTML
                resp2 = requests.get(
                    BASE_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"}
                )
                if resp2.status_code == 200:
                    soup = BeautifulSoup(resp2.text, "html.parser")
                    for item in soup.select(".opening, .job-tile, article"):
                        link = item.find("a")
                        if not link:
                            continue
                        title = link.text.strip()
                        href = urljoin(BASE_URL, link.get("href", ""))
                        jobs.append(
                            {
                                "company": self.company_name,
                                "title": title,
                                "location": "United Kingdom",
                                "url": href,
                                "source_url": BASE_URL,
                                "apply_url": href,
                                "job_seq_no": str(hash(href)),
                                "is_active": True,
                                "posted_date": None,
                            }
                        )
        except Exception as e:
            logger.error(f"[{self.site_key}] Error: {e}")

        logger.info(f"[{self.site_key}] Found {len(jobs)} jobs")
        return jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        for job in jobs:
            try:
                job_id = job.get("job_seq_no", "")
                api = f"https://api.smartrecruiters.com/v1/companies/UKCAA/postings/{job_id}"
                resp = requests.get(
                    api, timeout=20, headers={"Accept": "application/json"}
                )
                if resp.status_code == 200:
                    d = resp.json()
                    sections = d.get("jobAd", {}).get("sections", {})
                    desc_parts = []
                    for sec in [
                        "jobDescription",
                        "qualifications",
                        "additionalInformation",
                    ]:
                        text = sections.get(sec, {}).get("text", "")
                        if text:
                            desc_parts.append(
                                BeautifulSoup(text, "html.parser").get_text(
                                    " ", strip=True
                                )
                            )
                    job["description"] = "\n\n".join(desc_parts)[:3000]
            except Exception as e:
                logger.warning(f"[{self.site_key}] Desc error: {e}")
            await asyncio.sleep(0.3)
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
