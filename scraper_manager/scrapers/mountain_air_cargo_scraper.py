import asyncio
import logging
from typing import List, Dict
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class MountainAirCargoScraper(BaseScraper):
    """Scraper for Mountain Air Cargo using their hrmdirect portal (stateless/fast)."""

    def __init__(self, config: Dict, db_manager=None):
        super().__init__(config, site_key="mountain_air_cargo", db_manager=db_manager)
        self.base_url = "https://mountainaircargo.hrmdirect.com/employment/job-openings.php?search=true&&cust_sort1=170262"

    async def fetch_jobs(self) -> List[Dict]:
        """Fetch and parse jobs directly from the static HTML."""
        jobs = []

        try:
            logger.info(f"[{self.site_key}] Fetching jobs from {self.base_url}...")

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

            # Find the job listing table - hrmdirect often uses a table with class 'job-openings'
            # or just a list of links in the 'content' area.
            # Based on read_url_content, it's a list/table of links.

            job_links = []
            for a in soup.find_all("a", href=True):
                if "job-opening.php" in a["href"]:
                    title = a.text.strip()
                    if title and title not in [
                        "Department",
                        "Position Title",
                        "City",
                        "State",
                    ]:
                        job_links.append((title, urljoin(self.base_url, a["href"])))

            logger.info(
                f"[{self.site_key}] Found {len(job_links)} potential job links."
            )

            for title, job_url in job_links:
                # Need to check limits
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    logger.info(
                        f"[{self.site_key}] Reached max jobs limit ({self.max_jobs})"
                    )
                    break

                # Early filtering by title
                if not self.should_process_job(title):
                    continue

                # Duplicate check
                if await self.is_url_already_scraped(job_url):
                    continue

                # Fetch details for description and potentially location
                logger.info(f"[{self.site_key}] Fetching details for: {title}...")

                def fetch_detail():
                    return requests.get(
                        job_url,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        },
                        timeout=20.0,
                    )

                detail_resp = await asyncio.to_thread(fetch_detail)
                if detail_resp.status_code != 200:
                    logger.warning(
                        f"[{self.site_key}] Failed to fetch details for {title}"
                    )
                    continue

                detail_soup = BeautifulSoup(detail_resp.text, "html.parser")

                # Extract location - usually in a specific div or meta tag
                location = "Unknown"
                loc_tag = detail_soup.find(
                    "div", class_="job_location"
                ) or detail_soup.find("span", class_="location")
                if loc_tag:
                    location = loc_tag.text.strip()

                # Description
                desc_tag = detail_soup.find(
                    "div", id="job_description"
                ) or detail_soup.find("div", class_="job_description")
                description = str(desc_tag) if desc_tag else "Description not found."

                job = get_job_dict(
                    job_id=f"{self.site_key}_{hash(job_url)}",
                    title=title,
                    company=self.company_name,
                    location=location,
                    url=job_url,
                    source_url=self.base_url if hasattr(self, 'base_url') else job_url,
                    description=description,
                    apply_url=job_url,
                    source=self.site_key
                )
                jobs.append(job)

            logger.info(
                f"[{self.site_key}] Successfully parsed {len(jobs)} potential new jobs."
            )
            return jobs

        except Exception as e:
            logger.error(f"[{self.site_key}] Error during fetching: {e}")
            return jobs

    async def run(self):
        """Standard execution method."""
        self.print_header()

        jobs = await self.fetch_jobs()

        # Apply strict title filtering against our advanced manager
        matched_jobs, rejected_jobs, stats = self.apply_title_filter(jobs)

        # save_results in BaseScraper handles DB persisting
        await self.save_results(matched_jobs)

        return matched_jobs
