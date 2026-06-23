import asyncio
import logging
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class HeronaviationScraper(BaseScraper):
    """
    Scraper for Heron Aviation (WordPress / Elementor accordion)
    URL: https://www.heronaviation.com/de/jobs-karriere/
    Jobs are listed as accordion items on a single page, not separate URLs.
    """

    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="heronaviation", db_manager=db_manager)
        self.base_url = "https://www.heronaviation.com/de/jobs-karriere/"
        self.company_name = "Heron Aviation"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        try:
            resp = await asyncio.to_thread(
                requests.get,
                self.base_url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=20,
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            titles = soup.select("a.elementor-accordion-title")
            contents = soup.select("div.elementor-tab-content")

            for title_el, content_el in zip(titles, contents):
                title = title_el.get_text(strip=True)
                if not title:
                    continue

                description = content_el.get_text(separator="\n", strip=True)
                content_id = content_el.get("id", "")
                url = f"{self.base_url}#{content_id}" if content_id else self.base_url

                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break

                jobs.append(
                    get_job_dict(
                        job_id=f"heronaviation_{content_id or title}",
                        title=title,
                        company=self.company_name,
                        location="Germany/Spain",
                        url=url,
                        source_url=self.base_url,
                        apply_url=url,
                        description=description,
                        source=self.site_key,
                    )
                )
        except Exception as e:
            logger.error(f"[{self.site_key}] Failed to fetch jobs: {e}")

        logger.info(f"[{self.site_key}] Found {len(jobs)} jobs")
        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        if not jobs:
            return []
        if self.use_filter and self.filter_manager:
            jobs, _, _ = self.apply_title_filter(jobs)
            if not jobs:
                return []
        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []
        await self.save_results(jobs)
        return jobs
