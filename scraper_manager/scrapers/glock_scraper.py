import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class GlockScraper(BaseScraper):
    """
    Scraper for Glock Aviation
    URL: https://jobs.glock.at/programme/onlinebewerbung_uebersicht.php
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="glock", db_manager=db_manager)
        self.base_url = "https://jobs.glock.at/programme/onlinebewerbung_uebersicht.php"
        self.company_name = "Glock Aviation"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Fetching Glock careers page...")

        try:
            resp = requests.get(self.base_url, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            links = soup.find_all("a")
            for a in links:
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break

                href = a.get("href", "")
                if "onlinebewerbung_detail.php" in href:
                    text = a.text.strip().replace("\n", " ")
                    if not text or "Initiativ" in text:
                        continue

                    # Split title and location if possible (e.g. "Title  FERLACH")
                    # Usually separated by some weird whitespace or non-breaking spaces
                    parts = text.rsplit("\xa0", 1)
                    if len(parts) == 2:
                        title = parts[0].strip()
                        location = parts[1].strip() + ", Austria"
                    else:
                        title = text
                        location = "Austria"

                    url = urljoin(self.base_url, href)
                    job_id = (
                        href.split("objnr=")[-1] if "objnr=" in href else str(hash(url))
                    )

                    jobs.append(
                        {
                            "company": self.company_name,
                            "title": title,
                            "location": location,
                            "url": url,
                            "source_url": self.base_url,
                            "apply_url": url,
                            "is_active": True,
                            "job_seq_no": job_id,
                        }
                    )
        except Exception as e:
            logger.error(f"[{self.site_key}] Error fetching jobs: {e}")

        return jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        if not jobs:
            return []

        logger.info(
            f"[{self.site_key}] Fetching descriptions for {len(jobs)} matched jobs..."
        )

        for job in jobs:
            url = job["url"]

            try:
                resp = requests.get(url, timeout=20)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # Find main text container
                    content = soup.find("div", id="content") or soup.find("body")
                    if content:
                        text = content.text
                        import re

                        text = re.sub(r"\s+", " ", text).strip()
                        job["description"] = text
            except Exception as e:
                logger.warning(
                    f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}"
                )

            await asyncio.sleep(0.5)

        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        if not jobs:
            return []

        if self.use_filter and self.filter_manager:
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)
            if not jobs:
                return []

        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []

        jobs = await self.fetch_job_descriptions(jobs)
        await self.save_results(jobs)
        return jobs
