import logging
import asyncio
from typing import List, Dict
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class JetflyScraper(BaseScraper):
    """Scraper for Jetfly careers site using statically embedded HTML (fast)."""

    def __init__(self, config: Dict, db_manager=None):
        super().__init__(config, site_key="jetfly", db_manager=db_manager)
        self.base_url = "https://jetfly.com/apply-for-a-job"

    async def fetch_jobs(self) -> List[Dict]:
        """Fetch and parse jobs directly from the static HTML using curl_cffi."""
        jobs = []

        try:
            logger.info(f"[{self.site_key}] Fetching jobs from {self.base_url}...")

            import requests

            def fetch_url():
                return requests.get(
                    self.base_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    },
                    timeout=30.0,
                )

            response = await asyncio.to_thread(fetch_url)
            html_content = response.text

            if not html_content or response.status_code != 200:
                logger.error(
                    f"[{self.site_key}] Failed to retrieve HTML: Status {response.status_code}"
                )
                return jobs

            soup = BeautifulSoup(html_content, "html.parser")

            # Find all job cards
            job_cards = soup.find_all("div", class_="card-careers")
            logger.info(
                f"[{self.site_key}] Found {len(job_cards)} job cards on the page."
            )

            for card in job_cards:
                # Need to check limits
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    logger.info(
                        f"[{self.site_key}] Reached max jobs limit ({self.max_jobs})"
                    )
                    break

                # Extract link wrapper
                a_tag = card.find("a", href=True)
                if not a_tag:
                    continue

                job_url = a_tag["href"]

                # Make URL absolute if necessary
                if not job_url.startswith("http"):
                    job_url = urljoin(self.base_url, job_url)

                # Extract title
                title_tag = card.find("h3")
                if not title_tag:
                    continue
                title = title_tag.text.strip()

                # Early filtering: Should we even process this job?
                if not self.should_process_job(title):
                    continue

                # Duplicate check
                if await self.is_url_already_scraped(job_url):
                    continue

                # Extract location (optional)
                location = "Unknown"
                loc_div = card.find("div", class_="city-name")
                if loc_div:
                    location = loc_div.text.strip()

                # Extract type/duration (optional)
                job_type = ""
                dur_div = card.find("div", class_="duration")
                if dur_div:
                    job_type = dur_div.text.strip()

                job = get_job_dict(
                    job_id=f"{self.site_key}_{hash(job_url)}",
                    title=title,
                    company=self.company_name,
                    location=location,
                    url=job_url,
                    source_url=self.base_url if hasattr(self, 'base_url') else job_url,
                    description=f"Role: {title}\nType: {job_type}",
                    apply_url=job_url,
                    source=self.site_key
                )
                jobs.append(job)

            logger.info(
                f"[{self.site_key}] Successfully parsed {len(jobs)} potential new jobs to filter."
            )
            return jobs

        except Exception as e:
            logger.error(f"[{self.site_key}] Error during fetching: {e}")
            return jobs

    async def run(self):
        """Standard run flow tailored for fast static parsing."""
        self.print_header()

        jobs = await self.fetch_jobs()

        # Apply strict title filtering against our advanced manager
        matched_jobs, rejected_jobs, stats = self.apply_title_filter(jobs)

        # save_results in BaseScraper handles DB persisting
        await self.save_results(matched_jobs)

        return matched_jobs
