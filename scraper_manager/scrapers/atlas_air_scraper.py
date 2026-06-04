import asyncio
import logging
import re
import random
import html as html_lib
from curl_cffi import requests as curl_requests

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class AtlasAirScraper(BaseScraper):
    """
    Scraper for Atlas Air Worldwide (Greenhouse)
    URL: https://boards-api.greenhouse.io/v1/boards/atlasair/jobs
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="atlas_air", db_manager=db_manager)
        self.api_url = "https://boards-api.greenhouse.io/v1/boards/atlasair/jobs"
        self.company_name = "Atlas Air Worldwide"

    async def fetch_jobs(self) -> list:
        all_jobs = []

        try:
            logger.info(f"[{self.site_key}] Fetching Greenhouse API: {self.api_url}")
            # Greenhouse API is public and usually doesn't require complex headers
            response = curl_requests.get(self.api_url, impersonate=self.impersonate)

            if response.status_code != 200:
                logger.error(
                    f"[{self.site_key}] Failed to fetch API: Status {response.status_code}"
                )
                return []

            data = response.json()
            jobs_list = data.get("jobs", [])
            logger.info(f"[{self.site_key}] Found {len(jobs_list)} jobs in total API.")

            # Filter by max_jobs if necessary
            if self.max_jobs:
                jobs_list = jobs_list[: self.max_jobs]

            for job_entry in jobs_list:
                item_id = job_entry.get("id")
                title = job_entry.get("title", "")
                url = job_entry.get("absolute_url", "")
                location_data = job_entry.get("location", {})
                location = location_data.get("name", "Global")

                if not self.should_process_job(title):
                    continue

                if await self.is_url_already_scraped(url):
                    continue

                # Fetch detailed job info
                try:
                    detail_api_url = f"{self.api_url}/{item_id}"
                    logger.info(f"[{self.site_key}] Fetching detail for: {item_id}")

                    detail_res = curl_requests.get(
                        detail_api_url, impersonate=self.impersonate
                    )
                    if detail_res.status_code == 200:
                        detail_data = detail_res.json()
                        description_html = detail_data.get("content", "")
                        description = self.clean_html(description_html)

                        job = get_job_dict(
                            job_id=f"atlas_{item_id}",
                            title=title,
                            company=self.company_name,
                            location=location,
                            url=url,
                            source_url=self.api_url,
                            description=description,
                            apply_url=url,
                            posted_date=None,  # Updated field in GH?
                            source=self.site_key,
                        )

                        all_jobs.append(job)
                        # Respectful delay
                        await asyncio.sleep(
                            random.uniform(
                                self.request_delay_min, self.request_delay_max
                            )
                        )
                except Exception as e:
                    logger.error(
                        f"[{self.site_key}] Error fetching detail for {item_id}: {e}"
                    )
                    continue

        except Exception as e:
            logger.error(f"[{self.site_key}] Global error: {e}")

        return all_jobs

    def clean_html(self, html_content: str) -> str:
        """Improved HTML cleaner for Greenhouse descriptions"""
        if not html_content:
            return ""

        # Unescape HTML entities (like &quot;, &lt;, etc.)
        clean = html_lib.unescape(html_content)
        # Remove tags
        clean = re.sub(r"<[^>]*>", " ", clean)
        # Fix whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    def should_process_job(self, title: str) -> bool:
        """Custom logic if needed, otherwise use base filter"""
        return True  # Handled by run() calling apply_title_filter if needed

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        jobs = [j for j in jobs if j is not None]

        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs

    def print_header(self):
        print(f"\n{'=' * 50}")
        print(f"SCRAPER: {self.company_name} ({self.site_key})")
        print(f"{'=' * 50}")
