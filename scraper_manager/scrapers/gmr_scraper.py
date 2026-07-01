import asyncio
import logging
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

GMR_API_URL = "https://careers.gmr.net/api/jobs"
GMR_BASE_URL = "https://careers.gmr.net/gmr/jobs"
JOB_URL_TEMPLATE = "https://careers.gmr.net/gmr/jobs/{req_id}"


class GmrScraper(BaseScraper):
    """
    Scraper for Global Medical Response (GMR) (iCIMS REST API)
    URL: https://careers.gmr.net/gmr/jobs
    API: GET https://careers.gmr.net/api/jobs
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="gmr", db_manager=db_manager)
        self.base_url = GMR_BASE_URL
        self.company_name = "Global Medical Response (GMR)"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Querying GMR iCIMS API for jobs...")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }

        page = 1
        page_size = 50  # The API returns 10 by default regardless, paginate fully

        while True:
            try:
                params = {"num_items": page_size, "page": page}
                resp = await self.make_request(
                    GMR_API_URL,
                    method="GET",
                    params=params,
                    headers=headers,
                    timeout=20,
                )
                if not resp or resp.status_code != 200:
                    logger.warning(
                        f"[{self.site_key}] API returned {resp.status_code if resp else 'None'}"
                    )
                    break

                data = resp.json()
                batch = data.get("jobs", [])
                total = data.get("totalCount", 0)

                if not batch:
                    break

                for item in batch:
                    j = item.get("data", {})
                    req_id = j.get("req_id") or j.get("slug", "")
                    title = j.get("title", "Unknown")
                    city = j.get("city", "")
                    state = j.get("state", "")
                    country = j.get("country", "")
                    location = ", ".join(filter(None, [city, state, country])) or "Unknown"
                    description = BeautifulSoup(j.get("description", ""), "html.parser").get_text(" ", strip=True)
                    apply_url = j.get("apply_url", "")
                    job_url = JOB_URL_TEMPLATE.format(req_id=req_id) if req_id else GMR_BASE_URL

                    jobs.append(
                        {
                            "company": self.company_name,
                            "title": title,
                            "location": location,
                            "url": job_url,
                            "source_url": job_url,
                            "apply_url": apply_url or job_url,
                            "is_active": True,
                            "description": description[:5000],
                        }
                    )

                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break

                # Check if we've fetched all jobs
                fetched_so_far = (page - 1) * page_size + len(batch)
                if fetched_so_far >= total:
                    break

                page += 1

            except Exception as e:
                logger.error(f"[{self.site_key}] API extraction failed: {e}")
                break

        logger.info(f"[{self.site_key}] Found {len(jobs)} total jobs")
        return jobs

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

        # Descriptions are included in the list API - just save directly
        final_jobs = []
        for job in new_jobs:
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
            final_jobs.append(job_dict)

        await self.save_results(final_jobs)
        return final_jobs
