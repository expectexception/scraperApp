import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class FlixScraper(BaseScraper):
    """
    Scraper for Flix (FlixBus/FlixTrain)
    URL: https://flix.careers/de/standorte/berlin/#berlinjobs
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="flix", db_manager=db_manager)
        self.base_url = "https://flix.careers/de/standorte/berlin/"
        self.company_name = "Flix"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Fetching Flix Berlin jobs page...")

        try:
            resp = requests.get(self.base_url, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            job_links = soup.find_all("a", href=lambda h: h and "jobid=" in h)
            logger.info(f"[{self.site_key}] Found {len(job_links)} job entries")

            for a in job_links:
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break

                title_elem = a.find("h6")
                if not title_elem:
                    continue

                title = title_elem.text.strip()

                loc_elem = a.find("span", class_="location")
                location = loc_elem.text.strip() if loc_elem else "Berlin"

                url = urljoin(self.base_url, a.get("href"))

                # Extract jobid for sequence number
                job_id = url.split("jobid=")[-1] if "jobid=" in url else str(hash(url))

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
                    # Find main content div
                    content = (
                        soup.find("div", class_="job-detail")
                        or soup.find("main")
                        or soup.find("div", class_="entry-content")
                    )
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
