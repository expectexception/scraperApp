import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class FaktorScraper(BaseScraper):
    """
    Scraper for Faktor
    URL: https://www.wearefaktor.com/jobs
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="faktor", db_manager=db_manager)
        self.base_url = "https://www.wearefaktor.com/jobs"
        self.company_name = "Faktor"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Fetching Faktor jobs page...")

        try:
            resp = requests.get(self.base_url, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            job_items = soup.find_all("div", class_="p-p-core--job-card_component")
            logger.info(f"[{self.site_key}] Found {len(job_items)} job entries")

            for item in job_items:
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break

                title_elem = item.find("div", attrs={"fs-list-field": "role"})
                if not title_elem:
                    # fallback to finding the link text or heading
                    title_elem = item.find("h3") or item.find("h2")
                    if not title_elem:
                        continue

                title = title_elem.text.strip()

                link_elem = item.find("a", href=lambda h: h and "/jobs/" in h)
                if not link_elem:
                    continue

                url = urljoin(self.base_url, link_elem.get("href"))
                job_id = item.find("div", attrs={"fs-list-field": "bullhornid"})
                job_id = job_id.text.strip() if job_id else str(hash(url))

                # Try to get description right from the list view
                desc_elem = item.find("div", class_="p-p-core--jo-rtb")
                description = desc_elem.text.strip() if desc_elem else ""

                # location
                location = "Belgium"  # Default for Faktor

                jobs.append(
                    {
                        "company": self.company_name,
                        "title": title,
                        "location": location,
                        "url": url,
                        "source_url": self.base_url,
                        "apply_url": url,
                        "description": description,
                        "is_active": True,
                        "job_seq_no": job_id,
                    }
                )
        except Exception as e:
            logger.error(f"[{self.site_key}] Error fetching jobs: {e}")

        return jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        # Descriptions already extracted in fetch_jobs
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
