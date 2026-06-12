import logging
import requests

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class AstonjetScraper(BaseScraper):
    """
    Scraper for Astonjet (Recruitee API)
    URL: https://astonjet.recruitee.com/
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="astonjet", db_manager=db_manager)
        self.base_url = "https://astonjet.recruitee.com/"
        self.api_url = "https://astonjet.recruitee.com/api/offers"
        self.company_name = "Astonjet"

    async def fetch_jobs(self) -> list:
        """
        Scrape jobs from Astonjet Recruitee API
        """
        jobs = []

        try:
            logger.info(f"[{self.site_key}] Fetching jobs from {self.api_url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
            }
            
            resp = requests.get(self.api_url, headers=headers, timeout=30)
            resp.raise_for_status()

            data = resp.json()
            offers = data.get("offers", [])

            logger.info(f"[{self.site_key}] Found {len(offers)} job cards in API")

            for i, offer in enumerate(offers):
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break

                title = offer.get("title", "")
                if not self.should_process_job(title):
                    continue

                url = offer.get("careers_url", "")
                apply_url = offer.get("careers_apply_url", url)
                location = offer.get("location", "Unknown")
                desc = offer.get("description", "")
                if not desc:
                    desc = f"Astonjet career opportunity: {title}. Visit {url} for details."
                    
                job_id = f"astonjet_{offer.get('id', hash(url))}"

                job = get_job_dict(
                    job_id=job_id,
                    title=title,
                    company=offer.get("company_name", self.company_name),
                    location=location,
                    url=url,
                    source_url=self.base_url,
                    description=desc,
                    apply_url=apply_url,
                    posted_date=offer.get("published_at", ""),
                    source=self.site_key,
                )

                jobs.append(job)

        except Exception as e:
            logger.error(f"[{self.site_key}] Error scraping: {e}")
            import traceback
            logger.error(traceback.format_exc())

        return jobs

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
