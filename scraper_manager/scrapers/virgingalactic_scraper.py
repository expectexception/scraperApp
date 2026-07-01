import asyncio
import logging
import requests as sync_requests

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

WIDGETS_URL = "https://vgcareers.virgingalactic.com/widgets"
BASE_URL = "https://vgcareers.virgingalactic.com/global/en/search-results"
REF_NUM = "VGNVGEUS"
PAGE_ID = "page24"


class VirginGalacticScraper(BaseScraper):
    """
    Scraper for Virgin Galactic (Phenom People API)
    URL: https://vgcareers.virgingalactic.com/global/en/search-results
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="virgingalactic", db_manager=db_manager)
        self.base_url = BASE_URL
        self.company_name = "Virgin Galactic"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Querying Phenom People API for jobs...")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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
                "category",
                "country",
                "state",
                "city",
                "type",
                "employmentType",
            ],
            "pageName": "search-results",
            "size": 1000,
            "clearAll": False,
            "jdsource": "facets",
            "isSliderEnable": True,
            "pageId": PAGE_ID,
            "siteType": "external",
            "ddoKey": "refineSearch",
            "refNum": REF_NUM,
        }

        try:
            resp = await self.make_request(
                WIDGETS_URL,
                method="POST",
                json=payload,
                headers=headers,
                timeout=30,
            )
            if not resp or resp.status_code != 200:
                logger.warning(
                    f"[{self.site_key}] API returned {resp.status_code if resp else 'None'}"
                )
                return jobs

            data = resp.json()
            raw_jobs = data.get("refineSearch", {}).get("data", {}).get("jobs", [])
            logger.info(f"[{self.site_key}] API returned {len(raw_jobs)} jobs")

            for j in raw_jobs:
                job_id = j.get("jobId", "")
                link = f"https://vgcareers.virgingalactic.com/global/en/job/{job_id}"
                location = (
                    j.get("cityStateCountry")
                    or j.get("location")
                    or j.get("cityState")
                    or "Unknown"
                )

                jobs.append(
                    {
                        "company": self.company_name,
                        "title": j.get("title", "Unknown"),
                        "location": location,
                        "url": link,
                        "source_url": link,
                        "apply_url": j.get("applyUrl", link),
                        "is_active": True,
                        "description": j.get("descriptionTeaser", ""),
                        "job_seq_no": j.get("jobSeqNo"),
                    }
                )

        except Exception as e:
            logger.error(f"[{self.site_key}] API extraction failed: {e}")

        return jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        if not jobs:
            return []

        logger.info(
            f"[{self.site_key}] Fetching descriptions for {len(jobs)} matched jobs..."
        )

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        enriched = []
        for job in jobs:
            job_seq_no = job.pop("job_seq_no", None)
            if not job_seq_no:
                continue

            payload = {
                "jobSeqNo": job_seq_no,
                "ddoKey": "jobDetail",
                "refNum": REF_NUM,
            }

            try:
                resp = await self.make_request(
                    WIDGETS_URL,
                    method="POST",
                    json=payload,
                    headers=headers,
                    timeout=20,
                )
                if resp and resp.status_code == 200:
                    data = resp.json()
                    jdata = data.get("jobDetail", {}).get("data", {}).get("job", {})
                    full_desc = jdata.get("description") or jdata.get("jobDescription")
                    if full_desc:
                        job["description"] = full_desc

            except Exception as e:
                logger.warning(
                    f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}"
                )

            job_dict = get_job_dict(
                job_id=f"{self.site_key}_{hash(job['url'])}",
                title=job["title"],
                company=job["company"],
                location=job["location"],
                url=job["url"],
                source_url=self.base_url,
                description=job.get("description", ""),
                apply_url=job.get("apply_url", job["url"]),
                source=self.site_key,
            )
            enriched.append(job_dict)
            await asyncio.sleep(0.1)

        return enriched

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        if not jobs:
            return []

        matched_jobs, _, _ = self.apply_title_filter(jobs)
        if not matched_jobs:
            return []

        new_jobs, _ = await self.filter_new_jobs(matched_jobs)
        if not new_jobs:
            return []

        final_jobs = await self.fetch_job_descriptions(new_jobs)
        await self.save_results(final_jobs)
        return final_jobs
