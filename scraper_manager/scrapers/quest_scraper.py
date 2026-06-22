import logging
from scraper_manager.scrapers.fedex_scraper import FedexScraper

logger = logging.getLogger(__name__)

class QuestGlobalScraper(FedexScraper):
    """
    Scraper for Quest Global (Phenom People)
    URL: https://careers.quest-global.com/global/en
    """
    def __init__(self, config, db_manager=None):
        super().__init__(config, db_manager=db_manager, site_key="quest_global")
        self.company_name = "Quest Global"
