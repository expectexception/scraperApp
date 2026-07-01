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
        self.company_name = "Mountain Air Cargo"

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

                # Fetch details for description and location
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

                # Extract location from table.viewFields
                location = "USA"
                fields_table = detail_soup.find("table", class_="viewFields")
                if fields_table:
                    for row in fields_table.find_all("tr"):
                        cells = row.find_all(["td", "th"])
                        if len(cells) >= 2:
                            label = cells[0].get_text().strip()
                            val = cells[1].get_text().strip()
                            if "Location" in label:
                                location = val
                                break

                # Extract Description from div.jobDesc
                desc_tag = detail_soup.find("div", class_="jobDesc")
                if desc_tag:
                    description = desc_tag.get_text(separator="\n", strip=True)
                else:
                    description = "Description not found."

                job = get_job_dict(
                    job_id=f"{self.site_key}_{job_url.split('req=')[-1].split('&')[0]}" if "req=" in job_url else f"{self.site_key}_{hash(job_url)}",
                    title=title,
                    company=self.company_name,
                    location=location,
                    url=job_url,
                    source_url=self.base_url,
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

        await self.save_results(matched_jobs)

        return matched_jobs
