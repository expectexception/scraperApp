import logging
from typing import Dict
from .jpmc_scraper import JpmcScraper

logger = logging.getLogger(__name__)

class CargoluxScraper(JpmcScraper):
    """Scraper for Cargolux Oracle Cloud HCM job postings"""

    def __init__(self, config: Dict, db_manager=None):
        super().__init__(config, db_manager=db_manager)
        self.site_key = "cargolux"
        self.site_config = config.get("sites", {}).get("cargolux", {})
        self.base_url = self.site_config.get("base_url", "https://cargolux-iajigs.fa.ocs.oraclecloud.com")
        self.api_url = self.site_config.get(
            "api_url",
            "https://cargolux-iajigs.fa.ocs.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
        )
        self.site_number = self.site_config.get("site_number", "CargoluxGroundStaff")
        self.search_keyword = None
        
        # Override company name in job data extraction
    def _extract_job_data(self, job: Dict) -> Dict:
        job_data = super()._extract_job_data(job)
        job_data["company"] = "Cargolux"
        job_data["job_id"] = job_data["job_id"].replace("jpmc_", "cargolux_")
        return job_data
