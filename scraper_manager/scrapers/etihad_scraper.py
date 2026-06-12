import logging
from typing import List, Dict

from .smartrecruiters_scraper import SmartRecruitersScraper

logger = logging.getLogger(__name__)

class EtihadScraper(SmartRecruitersScraper):
    """
    Scraper for Etihad Airways using SmartRecruiters API.
    URL: https://careers.smartrecruiters.com/EtihadAirways5
    """

    def __init__(self, config: Dict, db_manager=None):
        super().__init__(config, site_key="etihad", db_manager=db_manager)
        self.company_id = "EtihadAirways5"
        self.company_name = "Etihad Airways"
        self.base_url = "https://careers.smartrecruiters.com/EtihadAirways5"
