import logging
import re

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class AirEuropaExpressScraper(BaseScraper):
    """
    Scraper for Air Europa Express.
    Original supplied URL was a 404. They use InfoJobs which has high bot protection.
    This scraper acts as a placeholder/fallback that safely returns an empty list.
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="aireuropaexpress", db_manager=db_manager)
        self.base_url = (
            "https://www.infojobs.net/air-europa/em-i138127453086788506161413812607"
        )
        self.company_name = "Air Europa Express"

    async def fetch_jobs(self) -> list:
        from curl_cffi import requests

        jobs = []

        try:
            logger.info(f"[{self.site_key}] Fetching Air Europa jobs via curl_cffi...")
            resp = requests.get(self.base_url, impersonate="chrome110", timeout=30)
            if resp.status_code == 200:
                # Look for potential job links
                matches = re.findall(
                    r'href="([^"]*(?:trabajo|empleo|career|job)[^"]*)"[^>]*>([^<]+)</a>',
                    resp.text,
                    re.I,
                )
                for href, title in matches:
                    if self.is_job_link(title, href):
                        url = (
                            href
                            if "http" in href
                            else f"https://www.aireuropa.com{href}"
                        )
                        job_id = url.strip("/").split("/")[-1]
                        jobs.append(
                            get_job_dict(
                                job_id=f"aireuropa_{job_id}",
                                title=title.strip(),
                                company=self.company_name,
                                location="Spain",
                                url=url,
                                description=f"Air Europa Job: {title.strip()}",
                                apply_url=url,
                                source=self.site_key,
                            )
                        )
        except Exception as e:
            logger.error(f"[{self.site_key}] Error: {e}")

        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()

        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
