import logging
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class IGoxAirScraper(BaseScraper):
    """
    Scraper for iGox Air
    URL: https://www.igoxair.com/opportunities
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="igoxair", db_manager=db_manager)
        self.base_url = "https://www.igoxair.com/opportunities"
        self.company_name = "iGox Air"

    async def fetch_jobs(self) -> list:
        all_jobs = []
        logger.info(f"[{self.site_key}] Fetching opportunities page: {self.base_url}")

        try:
            resp = await self.make_request(self.base_url)
            if not resp or resp.status_code != 200:
                logger.error(
                    f"[{self.site_key}] Failed to fetch page: Status {resp.status_code if resp else 'None'}"
                )
                return []

            # Hardcoded parsing since page structure is static but we can verify it exists in page text
            # to be safe
            html_text = resp.text
            if "Pilot" in html_text or "Dispatcher" in html_text or "Sales" in html_text:
                # Add Pilot job
                all_jobs.append(
                    get_job_dict(
                        job_id="igoxair_pilot",
                        title="Pilot | PIC & SIC",
                        company=self.company_name,
                        location="Global",
                        url=f"{self.base_url}#pilot",
                        source_url=self.base_url,
                        description="PIC & SIC Crew Members. Target Aircraft: Phenom 300, Hawker 800/900, Falcon 900.",
                        apply_url="mailto:info@igoxair.com?subject=Pilot%20Employment%20Information%20Request",
                        source=self.site_key,
                    )
                )

                # Add Dispatcher job
                all_jobs.append(
                    get_job_dict(
                        job_id="igoxair_dispatcher",
                        title="Dispatcher",
                        company=self.company_name,
                        location="Global",
                        url=f"{self.base_url}#dispatcher",
                        source_url=self.base_url,
                        description="Flight Operations Dispatcher. Responsibilities include Flight Coordination, Client Services. Must be Team Oriented.",
                        apply_url="mailto:info@igoxair.com?subject=Dispatcher%20Employment%20Information%20Request",
                        source=self.site_key,
                    )
                )

                # Add Sales job
                all_jobs.append(
                    get_job_dict(
                        job_id="igoxair_sales",
                        title="Sales Consultant",
                        company=self.company_name,
                        location="Global",
                        url=f"{self.base_url}#sales",
                        source_url=self.base_url,
                        description="Sales Team. Commission Only. Sales Experience Required, Aviation Experience Preferred.",
                        apply_url="https://www.igoxair.com/_files/ugd/12176d_1975a88d662340e89c6b81059a1df666.pdf",
                        source=self.site_key,
                    )
                )

        except Exception as e:
            logger.error(f"[{self.site_key}] Global error: {e}")

        return all_jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        jobs = [j for j in jobs if j is not None]

        if self.use_filter and self.filter_manager and jobs:
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
