import asyncio
import logging
from typing import List, Dict
import requests
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class SpiritScraper(BaseScraper):
    """Scraper for Spirit Airlines careers site using their internal JSON API."""

    def __init__(self, config: Dict, db_manager=None):
        super().__init__(config, site_key="spirit", db_manager=db_manager)
        self.api_url = "https://careers.spirit.com/api/jobs"
        self.base_url = "https://careers.spirit.com/careers-home/jobs"

    async def fetch_jobs(self) -> List[Dict]:
        """Fetch and parse jobs directly from the JSON API."""
        jobs = []
        page = 1

        try:
            while not self.max_pages or page <= self.max_pages:
                params = {
                    "page": page,
                    "sortBy": "relevance",
                    "descending": "false",
                    "internal": "false",
                    "domain": "spirit.jibeapply.com",
                }

                logger.info(f"[{self.site_key}] Fetching page {page} from API...")

                def fetch_api():
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Referer": self.base_url,
                        "Accept": "application/json",
                    }
                    return requests.get(
                        self.api_url, params=params, headers=headers, timeout=30.0
                    )

                response = await asyncio.to_thread(fetch_api)

                if response.status_code != 200:
                    logger.error(
                        f"[{self.site_key}] API returned status {response.status_code}"
                    )
                    break

                data = response.json()
                api_jobs = data.get("jobs", [])

                if not api_jobs:
                    logger.info(f"[{self.site_key}] No more jobs found on page {page}")
                    break

                logger.info(
                    f"[{self.site_key}] Found {len(api_jobs)} jobs on page {page}"
                )

                for job_item in api_jobs:
                    job_data = job_item.get("data", {})
                    title = job_data.get("title", "").strip()
                    req_id = job_data.get("req_id", job_data.get("slug", ""))

                    if not title or not req_id:
                        continue

                    # Early filtering by title
                    if not self.should_process_job(title):
                        continue

                    # Duplicate check
                    job_url = f"{self.base_url}/{req_id}"
                    if await self.is_url_already_scraped(job_url):
                        continue

                    # Extract details
                    description_html = job_data.get(
                        "description", job_data.get("responsibilities", "")
                    )
                    location = job_data.get(
                        "full_location", job_data.get("short_location", "Unknown")
                    )

                    job = get_job_dict(
                        job_id=f"{self.site_key}_{hash(job_url)}",
                        title=title,
                        company=self.company_name,
                        location=location,
                        url=job_url,
                        source_url=self.base_url if hasattr(self, 'base_url') else job_url,
                        description=description_html,
                        apply_url=job_url,
                        source=self.site_key
                    )
                    jobs.append(job)

                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        logger.info(
                            f"[{self.site_key}] Reached max jobs limit ({self.max_jobs})"
                        )
                        return jobs

                page += 1

            logger.info(
                f"[{self.site_key}] Successfully parsed {len(jobs)} jobs from API."
            )
            return jobs

        except Exception as e:
            logger.error(f"[{self.site_key}] Error during API fetching: {e}")
            return jobs

    async def run(self):
        """Standard run flow for API-based scraper."""
        self.print_header()

        jobs = await self.fetch_jobs()

        # Apply strict title filtering against our advanced manager
        matched_jobs, rejected_jobs, stats = self.apply_title_filter(jobs)

        # save_results in BaseScraper handles DB persisting
        await self.save_results(matched_jobs)

        return matched_jobs
