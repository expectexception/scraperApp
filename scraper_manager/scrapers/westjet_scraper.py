import logging
from typing import Dict
from .dayforce_scraper import DayforceScraper

logger = logging.getLogger(__name__)


class WestJetScraper(DayforceScraper):
    """Scraper for WestJet (Dayforce HCM)."""

    def __init__(self, config: Dict, db_manager=None):
        super().__init__(config, db_manager=db_manager, site_key="westjet")
