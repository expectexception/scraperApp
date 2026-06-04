import asyncio
import logging
import requests
import json
import re
import html

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class MaltairportScraper(BaseScraper):
    """
    Scraper for Malta Airport
    URL: https://maltairport.com/corporate/careers/join-our-team/
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="maltairport", db_manager=db_manager)
        self.base_url = "https://maltairport.com/corporate/careers/join-our-team/"
        self.company_name = "Malta Airport"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Fetching Malta Airport careers page...")

        try:
            resp = requests.get(self.base_url, timeout=30)
            resp.raise_for_status()

            # Find the jobListingFilter JSON
            match = re.search(r"jobListingFilter\(\s*(\[.*?\])\s*\)", resp.text)
            if match:
                json_str = html.unescape(match.group(1))
                jobs_data = json.loads(json_str)
                logger.info(
                    f"[{self.site_key}] Found {len(jobs_data)} jobs in JSON payload"
                )

                for j in jobs_data:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    title = j.get("title", "Unknown")
                    url = j.get("url", "")

                    if not url:
                        continue

                    job_id = j.get("id", str(hash(url)))

                    jobs.append(
                        {
                            "company": self.company_name,
                            "title": title,
                            "location": "Malta",
                            "url": url,
                            "source_url": self.base_url,
                            "apply_url": url,
                            "is_active": True,
                            "job_seq_no": job_id,
                        }
                    )
            else:
                logger.warning(
                    f"[{self.site_key}] Could not find jobListingFilter JSON in page source"
                )

        except Exception as e:
            logger.error(f"[{self.site_key}] Error fetching jobs: {e}")

        return jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        if not jobs:
            return []

        logger.info(
            f"[{self.site_key}] Fetching descriptions for {len(jobs)} matched jobs from Workable..."
        )

        for job in jobs:
            url = job["url"]

            try:
                resp = requests.get(url, timeout=20)
                if resp.status_code == 200:
                    # The link goes to maltairport.workable.com
                    from bs4 import BeautifulSoup

                    soup = BeautifulSoup(resp.text, "html.parser")

                    # Workable descriptions
                    desc_elem = (
                        soup.find("main")
                        or soup.find("div", class_="job-description")
                        or soup.find("body")
                    )
                    if desc_elem:
                        # Clean up text
                        text = desc_elem.text
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
