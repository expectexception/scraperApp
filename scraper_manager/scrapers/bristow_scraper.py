import logging
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class BristowScraper(BaseScraper):
    """
    Scraper for Bristow Helicopters.
    The provided URL is a LinkedIn jobs page. LinkedIn requires a dedicated session/API.
    The main LinkedIn scraper should be used to target this instead. Safely returning empty.
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='bristow', db_manager=db_manager)
        self.base_url = "https://www.linkedin.com/company/bristow-group-inc/jobs"
        self.company_name = "Bristow Helicopters"

    async def fetch_jobs(self) -> list:
        logger.info(f"[{self.site_key}] Target is LinkedIn. Use the dedicated LinkedIn scraper configuration instead. Returning 0.")
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
