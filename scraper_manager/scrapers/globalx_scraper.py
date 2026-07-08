import logging
import re
from datetime import datetime
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class GlobalXScraper(BaseScraper):
    """
    Scraper for GlobalX Airlines (ADP Workforce Now)
    URL: https://globalxair.com/careers/
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="globalx", db_manager=db_manager)
        self.cid = "6ad752d0-c351-4566-8bab-f4d900fc65c3"
        self.ccid = "19000101_000001"
        self.base_url = f"https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid={self.cid}&ccId={self.ccid}&lang=en_US"
        self.api_url = f"https://workforcenow.adp.com/mascsr/default/careercenter/public/events/staffing/v1/job-requisitions?cid={self.cid}&ccId={self.ccid}&lang=en_US"
        self.detail_api_base = "https://workforcenow.adp.com/mascsr/default/careercenter/public/events/staffing/v1/job-requisitions"
        self.company_name = "GlobalX"

    async def fetch_jobs(self) -> list:
        jobs = []
        try:
            logger.info(f"[{self.site_key}] Fetching from ADP API: {self.api_url}")
            response = await self.make_request(self.api_url)
            if not response or response.status_code != 200:
                logger.error(
                    f"[{self.site_key}] Failed to fetch from ADP API: Status {response.status_code if response else 'None'}"
                )
                return []

            data = response.json()
            requisitions = data.get("jobRequisitions", [])
            logger.info(f"[{self.site_key}] Found {len(requisitions)} jobs in ADP API")

            for req in requisitions:
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break

                item_id = req.get("itemID")
                title = req.get("requisitionTitle")
                if not item_id or not title:
                    continue

                location = "Miami, FL"
                locations = req.get("requisitionLocations", [])
                if locations and isinstance(locations, list):
                    loc_parts = []
                    address = locations[0].get("address", {})
                    if address.get("cityName"):
                        loc_parts.append(address.get("cityName"))
                    sub = address.get("countrySubdivisionLevel1", {})
                    if sub.get("codeValue"):
                        loc_parts.append(sub.get("codeValue"))
                    if loc_parts:
                        location = ", ".join(loc_parts)

                post_date = req.get("postDate", datetime.now().isoformat())
                job_url = f"{self.base_url}&jobId={item_id}"
                job_id = f"globalx_{item_id}"

                jobs.append(
                    {
                        "job_id": job_id,
                        "title": title,
                        "company": self.company_name,
                        "source": self.site_key,
                        "url": job_url,
                        "apply_url": job_url,
                        "location": location,
                        "timestamp": post_date,
                        "description": "",
                        "raw_id": item_id,
                    }
                )

        except Exception as e:
            logger.error(f"[{self.site_key}] Error fetching from ADP API: {e}")

        return jobs

    async def fetch_job_descriptions(self, jobs: list) -> list:
        if not jobs:
            return jobs

        logger.info(f"[{self.site_key}] Fetching descriptions for {len(jobs)} jobs...")

        for job in jobs:
            try:
                item_id = job.get("raw_id")
                if not item_id:
                    continue

                detail_url = f"{self.detail_api_base}/{item_id}?cid={self.cid}&ccId={self.ccid}&lang=en_US"
                response = await self.make_request(detail_url)
                if response and response.status_code == 200:
                    data = response.json()
                    html_desc = data.get("requisitionDescription", "")
                    if html_desc:
                        soup = BeautifulSoup(html_desc, "html.parser")
                        job["description"] = soup.get_text(separator="\n", strip=True)

            except Exception as e:
                logger.warning(
                    f"[{self.site_key}] Failed to fetch description for {job['url']}: {e}"
                )

        return jobs

    async def run(self):
        self.print_header()
        jobs_raw = await self.fetch_jobs()
        jobs = [get_job_dict(**job) for job in jobs_raw]

        if not jobs:
            return []

        if self.use_filter and self.filter_manager:
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)
            if not jobs:
                return []

        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []

        jobs = await self.fetch_job_descriptions(jobs)
        await self.save_results(jobs)
        return jobs
