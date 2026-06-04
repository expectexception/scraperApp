"""
EUROCONTROL Careers scraper — jobs.eurocontrol.int
Uses the iCIMS-based job board JSON API.
"""

import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://jobs.eurocontrol.int"
# iCIMS JSON search endpoint used by the portal
SEARCH_URL = "https://jobs.eurocontrol.int/jobs/search?ss=1&searchId=0&hashed=0"


class EurocontrolScraper(BaseScraper):
    """EUROCONTROL Careers (iCIMS portal)."""

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="eurocontrol", db_manager=db_manager)
        self.company_name = "EUROCONTROL"
        self.base_url = BASE_URL

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Fetching EUROCONTROL careers...")

        try:
            # iCIMS portals expose a JSON search endpoint
            api_url = f"{BASE_URL}/jobs/search?ss=1&in_iframe=1"
            resp = requests.get(
                api_url,
                timeout=30,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "X-Requested-With": "XMLHttpRequest",
                },
            )

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    postings = data.get("postings", data.get("results", []))
                    if not postings:
                        raise ValueError("No postings in JSON")
                    for p in postings:
                        title = p.get("title", "").strip()
                        job_id = str(p.get("id", hash(title)))
                        location = p.get("location", "Europe")
                        if (
                            not location.endswith("Europe")
                            and "Belgium" not in location
                        ):
                            location = f"{location}, Europe"
                        url = urljoin(BASE_URL, p.get("url", f"/jobs/details/{job_id}"))
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
                                "posted_date": p.get("datePosted", "")[:10] or None,
                            }
                        )
                except (ValueError, KeyError):
                    # Fallback: parse HTML
                    soup = BeautifulSoup(resp.text, "html.parser")
                    self._parse_html(soup, jobs)
            else:
                logger.warning(f"[{self.site_key}] HTTP {resp.status_code}")

        except Exception as e:
            logger.error(f"[{self.site_key}] Error: {e}")

        logger.info(f"[{self.site_key}] Found {len(jobs)} jobs")
        return jobs

    def _parse_html(self, soup, jobs):
        rows = soup.select("tr.data-row, div.job-listing, li.job")
        for row in rows:
            link = row.find("a")
            if not link:
                continue
            title = link.text.strip()
            href = urljoin(BASE_URL, link.get("href", ""))
            location_elem = row.select_one(".location, .col-location")
            location = (
                location_elem.text.strip() if location_elem else "Brussels, Belgium"
            )
            job_id = str(hash(href))
            jobs.append(
                {
                    "company": self.company_name,
                    "title": title,
                    "location": location + ", Belgium"
                    if "Belgium" not in location
                    else location,
                    "url": href,
                    "source_url": BASE_URL,
                    "apply_url": href,
                    "job_seq_no": job_id,
                    "is_active": True,
                    "posted_date": None,
                }
            )

    async def fetch_job_descriptions(self, jobs) -> list:
        for job in jobs:
            try:
                resp = requests.get(
                    job["url"], timeout=20, headers={"User-Agent": "Mozilla/5.0"}
                )
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    desc = (
                        soup.find("div", class_="iCIMS_InfoMsg_Job")
                        or soup.find("div", id="job-description")
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
