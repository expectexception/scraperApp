import logging
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class BlueIslandsScraper(BaseScraper):
    """
    Scraper for Blue Islands.
    NOTE: As of November 2025, Blue Islands has ceased operations and suspended all flights.
    Site is currently parked/defunct.
    Returning empty list.
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='blueislands', db_manager=db_manager)
        self.base_url = "https://www.airlinestaffrates.com/blue-islands-is-hiring-cabin-crew-channel-islands/"
        self.company_name = "Blue Islands"

    async def fetch_jobs(self) -> list:
        logger.info(f"[{self.site_key}] Airline ceased operations (Nov 2025). Returning 0.")
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
