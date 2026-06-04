import asyncio
import logging
import requests
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class JostScraper(BaseScraper):
    """
    Scraper for Jost Group
    URL: https://jostgroup.com/en/jobs
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="jost", db_manager=db_manager)
        self.base_url = "https://jostgroup.com/en/jobs"
        self.company_name = "Jost Group"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Fetching Jost Group careers page...")

        try:
            resp = requests.get(self.base_url, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            job_items = soup.find_all("li", class_="job-item")
            logger.info(f"[{self.site_key}] Found {len(job_items)} job entries")

            for item in job_items:
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break

                title_elem = item.find("h2", class_="jobs__item-title")
                if not title_elem:
                    continue

                title = title_elem.text.strip()

                info_elem = item.find("p")
                location = "Unknown"
                if info_elem:
                    parts = info_elem.text.split("-")
                    if len(parts) >= 2:
                        location = parts[1].strip()

                link_elem = item.find("a", class_="btn-secondary")
                if not link_elem:
                    continue

                url = link_elem.get("href", "")
                job_id = item.get("data-id", str(hash(url)))

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
                    # Main content usually in article or specific div
                    content = (
                        soup.find("div", class_="col-12 col-md-9")
                        or soup.find("article")
                        or soup.find("main")
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
