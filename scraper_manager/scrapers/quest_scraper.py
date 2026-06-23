import logging
from scraper_manager.scrapers.fedex_scraper import FedexScraper

logger = logging.getLogger(__name__)

class QuestGlobalScraper(FedexScraper):
    """
    Scraper for Quest Global (Phenom People)
    URL: https://careers.quest-global.com/global/en
    """

    # Quest Global runs a newer Phenom People widget version than careers.fedex.com,
    # so the old ".results-list__item" markup (verified stale as of 2026-06) doesn't
    # exist on this tenant. Override with the current widget's selectors.
    job_item_selector = ".jobs-list-item"
    job_link_selector = 'a[data-ph-at-id="job-link"]'
    job_location_selector = ".job-location, .job-multi_location"

    def __init__(self, config, db_manager=None):
        super().__init__(config, db_manager=db_manager, site_key="quest_global")
        self.company_name = "Quest Global"
