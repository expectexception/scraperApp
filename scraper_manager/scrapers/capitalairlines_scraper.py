import logging
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class CapitalAirlinesScraper(BaseScraper):
    """
    Scraper for Beijing Capital Airlines.
    Recruitment is heavily outsourced or not directly accessible via a central ATS.
    Safely returning empty for this placeholder.
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='capitalairlines', db_manager=db_manager)
        self.base_url = "https://jdair.net"
        self.company_name = "Beijing Capital Airlines"

    async def fetch_jobs(self) -> list:
        logger.info(f"[{self.site_key}] Recruitment handled by third parties. Safe Fallback Returning 0 jobs.")
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
