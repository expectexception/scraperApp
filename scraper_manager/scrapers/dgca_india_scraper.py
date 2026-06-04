"""
DGCA India (Directorate General of Civil Aviation) scraper.
Scrapes official vacancy notices from dgca.gov.in.
"""

import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.dgca.gov.in"
VACANCIES_URL = "https://www.dgca.gov.in/digigov-files/Vacancies"
JOBS_PAGE = "https://www.dgca.gov.in/digigov-files/jsp/sm/vacancies.jsp"


class DgcaIndiaScraper(BaseScraper):
    """DGCA India official vacancy notices scraper."""

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="dgca_india", db_manager=db_manager)
        self.company_name = "DGCA India"
        self.base_url = BASE_URL

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Fetching DGCA India vacancies...")

        urls_to_try = [
            JOBS_PAGE,
            f"{BASE_URL}/digigov-files/jsp/sm/vacancies.jsp",
            f"{BASE_URL}/content/vacancies",
        ]

        for url in urls_to_try:
            try:
                resp = requests.get(
                    url,
                    timeout=30,
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "Accept-Language": "en-IN,en;q=0.9",
                    },
                )
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                # DGCA typically has a table of vacancies
                rows = soup.select("table tr, .vacancy-item, li.vacancy")
                if not rows:
                    rows = soup.find_all("tr")

                for row in rows[1:]:  # skip header
                    cells = row.find_all("td")
                    if not cells:
                        continue

                    # Try to find a link and title
                    link = row.find("a")
                    if not link:
                        continue

                    title = link.text.strip()
                    if not title or len(title) < 5:
                        # Try first cell text
                        title = cells[0].text.strip()
                    if not title:
                        continue

                    href = urljoin(BASE_URL, link.get("href", ""))
                    job_id = str(hash(href))
                    location = "New Delhi, India"  # DGCA HQ
                    cells[-1].text.strip() if len(cells) > 1 else ""

                    jobs.append(
                        {
                            "company": self.company_name,
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

                if jobs:
                    break  # Found jobs, stop trying URLs

            except Exception as e:
                logger.error(f"[{self.site_key}] Error at {url}: {e}")

        logger.info(f"[{self.site_key}] Found {len(jobs)} vacancies")
        return jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        for job in jobs:
            try:
                if job["url"].endswith((".pdf", ".PDF")):
                    job["description"] = "See PDF attachment for full job description."
                    continue
                resp = requests.get(
                    job["url"], timeout=20, headers={"User-Agent": "Mozilla/5.0"}
                )
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    desc = (
                        soup.find("main")
                        or soup.find("div", class_="content")
                        or soup.find("body")
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
