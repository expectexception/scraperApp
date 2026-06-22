import logging
from .jpmc_scraper import JpmcScraper

logger = logging.getLogger(__name__)

class AdaniScraper(JpmcScraper):
    """Scraper for Adani Airports Oracle Cloud HCM"""
    def __init__(self, config, db_manager=None):
        super().__init__(config, db_manager=db_manager, site_key="adani_airports")
