import logging
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class EasternAirwaysScraper(BaseScraper):
    """
    Scraper for Eastern Airways.
    Site returns persistent 503 errors and blocks all automated headless headless connections (strict WAF).
    Safely returning empty for this placeholder to avoid constant bot blocks.
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='easternairways', db_manager=db_manager)
        self.base_url = "https://www.easternairways.com/careers"
        self.company_name = "Eastern Airways"

    async def fetch_jobs(self) -> list:
        logger.info(f"[{self.site_key}] WAF blocks automated access (503). Safe fallback returning 0 jobs.")
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
