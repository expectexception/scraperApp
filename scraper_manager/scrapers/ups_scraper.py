import asyncio
import logging
from typing import List, Dict, Any
import requests

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class UPSScraper(BaseScraper):
    """
    Scraper for UPS Airlines Careers
    URL: https://www.jobs-ups.com/search-jobs
    Platform: Taleo/Phenom
    """

    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="ups", db_manager=db_manager)
        self.base_url = "https://www.jobs-ups.com/global/en/search-results"
        self.company_name = "UPS Airlines"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Scrape jobs from UPS careers page
        """
        jobs = []
        jobs = []

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "sortBy": "",
            "subsearch": "",
            "from": 0,
            "jobs": True,
            "counts": True,
            "all_fields": [
                "phLocSlider",
                "category",
                "country",
                "state",
                "city",
                "type",
                "employmentType",
                "jobLevel",
            ],
            "pageName": "search-results",
            "size": 1000,
            "clearAll": False,
            "jdsource": "facets",
            "isSliderEnable": True,
            "pageId": "page4",
            "siteType": "external",
            "ddoKey": "refineSearch",
            "refNum": "UPBUPSGLOBAL",
        }

        try:
            logger.info(
                f"[{self.site_key}] Querying Phenom API endpoint directly for jobs..."
            )
            resp = requests.post(
                "https://www.jobs-ups.com/widgets",
                headers=headers,
                json=payload,
                timeout=30,
            )
            data = resp.json()
            raw_jobs = data.get("refineSearch", {}).get("data", {}).get("jobs", [])

            logger.info(f"[{self.site_key}] API returned {len(raw_jobs)} jobs")

            for j in raw_jobs:
                link = f"https://www.jobs-ups.com/global/en/job/{j.get('jobId')}"
                jobs.append(
                    {
                        "company": self.company_name,
                        "title": j.get("title", "Unknown"),
                        "location": j.get("location", "United States"),
                        "url": link,
                        "source_url": link,
                        "apply_url": link,
                        "is_active": True,
                        "description": j.get("descriptionTeaser", ""),
                        "job_seq_no": j.get(
                            "jobSeqNo"
                        ),  # Need this for the details API
                    }
                )
        except Exception as e:
            logger.error(f"[{self.site_key}] API extraction failed: {e}")

        return jobs

    async def fetch_job_descriptions(
        self, jobs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Fetch full details for matched jobs only"""
        if not jobs:
            return []

        logger.info(
            f"[{self.site_key}] Fetching descriptions for {len(jobs)} matched jobs via API..."
        )

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        for job in jobs:
            job_seq_no = job.pop("job_seq_no", None)
            if not job_seq_no:
                continue

            payload = {
                "jobSeqNo": job_seq_no,
                "ddoKey": "jobDetail",
                "refNum": "UPBUPSGLOBAL",
            }

            try:
                resp = requests.post(
                    "https://www.jobs-ups.com/widgets",
                    headers=headers,
                    json=payload,
                    timeout=20,
                )
                data = resp.json()
                jdata = data.get("jobDetail", {}).get("data", {}).get("job", {})

                # Try to get the detailed description if available
                full_desc = jdata.get("description") or jdata.get("jobDescription")
                if full_desc:
                    job["description"] = full_desc

            except Exception as e:
                logger.warning(
                    f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}"
                )

            # No playwright needed, so no sleep required but we'll add a tiny delay to be nice
            await asyncio.sleep(0.1)

        return jobs

    async def run(self):
        """Main execution method"""
        self.print_header()

        jobs = await self.fetch_jobs()
        if not jobs:
            return []

        if self.use_filter and self.filter_manager:
            logger.info(f"[{self.site_key}] Applying pre-filter...")
            matched_jobs, rejected_jobs, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)
            if not matched_jobs:
                return []
            jobs = matched_jobs

        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []

        jobs = await self.fetch_job_descriptions(jobs)
        await self.save_results(jobs)
        return jobs
