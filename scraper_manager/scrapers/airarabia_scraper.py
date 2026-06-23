import asyncio
import logging
import requests
from typing import List, Dict
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class AirArabiaScraper(BaseScraper):
    """
    Scraper for Air Arabia Group (Phenom People API)
    URL: https://www.airarabiagroupcareers.com/gb/en/search-results
    """

    def __init__(self, config: Dict, db_manager=None, is_auh: bool = False):
        site_key = "airarabia_auh" if is_auh else "airarabia"
        super().__init__(config, site_key=site_key, db_manager=db_manager)
        self.base_url = "https://www.airarabiagroupcareers.com/gb/en/search-results"
        self.company_name = "Air Arabia"
        self.is_auh = is_auh

    async def fetch_jobs(self) -> List[Dict]:
        jobs = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Size 1000 to get a large block of jobs at once
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
                "jobLevel",
            ],
            "pageName": "search-results",
            "size": 1000,
            "clearAll": False,
            "jdsource": "facets",
            "isSliderEnable": True,
            "pageId": "page3",
            "siteType": "external",
            "ddoKey": "refineSearch",
            "refNum": "AIRARABIA",
        }

        try:
            logger.info(
                f"[{self.site_key}] Querying Phenom API endpoint directly for jobs..."
            )
            resp = requests.post(
                "https://www.airarabiagroupcareers.com/widgets",
                headers=headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            raw_jobs = data.get("refineSearch", {}).get("data", {}).get("jobs", [])

            logger.info(f"[{self.site_key}] API returned {len(raw_jobs)} jobs")

            for j in raw_jobs:
                location = j.get("cityStateCountry") or j.get("location") or "Unknown"

                if self.is_auh:
                    location_blob = " ".join(
                        [location, j.get("city", "") or ""]
                        + (j.get("multi_location") or [])
                    ).lower()
                    if "abu dhabi" not in location_blob:
                        continue

                link = f"https://www.airarabiagroupcareers.com/gb/en/job/{j.get('jobId')}"

                jobs.append(
                    {
                        "company": j.get("companyName", self.company_name),
                        "title": j.get("title", "Unknown"),
                        "location": location,
                        "url": link,
                        "source_url": link,
                        "apply_url": link,
                        "is_active": True,
                        "description": j.get("descriptionTeaser", ""),
                        "job_seq_no": j.get("jobSeqNo"),
                    }
                )
        except Exception as e:
            logger.error(f"[{self.site_key}] API extraction failed: {e}")

        return jobs

    async def fetch_job_descriptions(self, jobs: List[Dict]) -> List[Dict]:
        if not jobs:
            return []

        logger.info(
            f"[{self.site_key}] Fetching descriptions for {len(jobs)} matched jobs via API..."
        )

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        enriched_jobs = []
        for job in jobs:
            job_seq_no = job.pop("job_seq_no", None)
            if not job_seq_no:
                continue

            payload = {
                "jobSeqNo": job_seq_no,
                "ddoKey": "jobDetail",
                "refNum": "AIRARABIA",
            }

            try:
                resp = requests.post(
                    "https://www.airarabiagroupcareers.com/widgets",
                    headers=headers,
                    json=payload,
                    timeout=20,
                )
                resp.raise_for_status()
                data = resp.json()
                jdata = data.get("jobDetail", {}).get("data", {}).get("job", {})

                full_desc = jdata.get("description") or jdata.get("jobDescription")
                if full_desc:
                    job["description"] = full_desc

                job_dict = get_job_dict(
                    job_id=f"{self.site_key}_{hash(job['url'])}",
                    title=job["title"],
                    company=job["company"],
                    location=job["location"],
                    url=job["url"],
                    source_url=self.base_url,
                    description=job["description"],
                    apply_url=job["url"],
                    source=self.site_key
                )
                enriched_jobs.append(job_dict)

            except Exception as e:
                logger.warning(
                    f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}"
                )

            await asyncio.sleep(0.1)

        return enriched_jobs

    async def run(self):
        self.print_header()

        jobs = await self.fetch_jobs()
        if not jobs:
            return []

        # Filter by title
        matched_jobs, rejected_jobs, stats = self.apply_title_filter(jobs)
        if not matched_jobs:
            return []

        # Filter out already scraped
        new_jobs, _ = await self.filter_new_jobs(matched_jobs)
        if not new_jobs:
            return []

        # Fetch details
        final_jobs = await self.fetch_job_descriptions(new_jobs)
        await self.save_results(final_jobs)
        return final_jobs
