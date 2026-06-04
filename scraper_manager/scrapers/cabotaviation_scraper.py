import logging
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class CabotAviationScraper(BaseScraper):
    """
    Scraper for Cabot Aviation.
    The provided URL is a general site without a dedicated careers board.
    Safely returning empty for this placeholder.
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="cabotaviation", db_manager=db_manager)
        self.base_url = "https://cabotaviation.com/"
        self.company_name = "Cabot Aviation"

    async def fetch_jobs(self) -> list:
        logger.info(
            f"[{self.site_key}] No dedicated ATS/Careers board found. Returning 0."
        )
        return []

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()

        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
