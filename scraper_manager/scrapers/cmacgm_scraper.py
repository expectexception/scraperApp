import logging
from typing import Dict
from .cevalogistics_scraper import CevaLogisticsScraper

logger = logging.getLogger(__name__)


class CmacgmScraper(CevaLogisticsScraper):
    """Scraper for CMA CGM (SuccessFactors portal)."""

    def __init__(self, config: Dict, db_manager=None):
        # We can just reuse CevaLogisticsScraper but with a different site_key and base_url
        super().__init__(config, db_manager=db_manager)
        self.site_key = "cmacgm"
        self.site_config = config.get("sites", {}).get("cmacgm", {})
        self.base_url = self.site_config.get("base_url", "https://jobs.cmacgm-group.com")
        self.jobs_url = self.site_config.get(
            "jobs_url",
            "https://jobs.cmacgm-group.com/search/?createNewAlert=false&q=&locationsearch=&optionsFacetsDD_shifttype="
        )
