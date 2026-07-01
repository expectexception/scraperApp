import asyncio
import logging

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class AaRegionalScraper(BaseScraper):
    """
    Scraper for American Airlines Regional (Workday)
    URL: https://aaregional.wd503.myworkdayjobs.com/search
    API: POST https://aaregional.wd503.myworkdayjobs.com/wday/cxs/aaregional/search/jobs
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="aaregional", db_manager=db_manager)
        self.base_url = "https://aaregional.wd503.myworkdayjobs.com/en-US/search"
        self.company_name = "American Airlines Regional"
        self.api_url = "https://aaregional.wd503.myworkdayjobs.com/wday/cxs/aaregional/search/jobs"
        self.detail_api_url = "https://aaregional.wd503.myworkdayjobs.com/wday/cxs/aaregional/search"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Querying Workday API for jobs...")

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        limit = 20
        offset = 0
        total = None

        while True:
            if self.max_jobs and len(jobs) >= self.max_jobs:
                break

            payload = {
                "appliedFacets": {},
                "limit": limit,
                "offset": offset,
                "searchText": "",
            }

            try:
                resp = await self.make_request(
                    self.api_url,
                    method="POST",
                    json=payload,
                    headers=headers,
                    timeout=20,
                )
                if not resp or resp.status_code != 200:
                    logger.warning(
                        f"[{self.site_key}] API returned status {resp.status_code if resp else 'None'}"
                    )
                    break

                data = resp.json()

                if total is None:
                    total = data.get("total", 0)

                postings = data.get("jobPostings", [])
                if not postings or offset >= total:
                    break

                for j in postings:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    external_path = j.get("externalPath", "")
                    url = f"https://aaregional.wd503.myworkdayjobs.com/en-US/search{external_path}"

                    jobs.append(
                        {
                            "company": self.company_name,
                            "title": j.get("title", "Unknown"),
                            "location": j.get("locationsText", "Unknown"),
                            "url": url,
                            "source_url": url,
                            "apply_url": url,
                            "is_active": True,
                            "job_seq_no": external_path,
                        }
                    )

                offset += limit

            except Exception as e:
                logger.error(f"[{self.site_key}] API extraction failed: {e}")
                break

        logger.info(f"[{self.site_key}] Found {len(jobs)} total jobs")
        return jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        if not jobs:
            return []

        logger.info(
            f"[{self.site_key}] Fetching descriptions for {len(jobs)} matched jobs..."
        )
        headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}

        async def fetch_desc(job):
            external_path = job.pop("job_seq_no", None)
            if not external_path:
                return
            try:
                detail_url = f"{self.detail_api_url}{external_path}"
                resp = await self.make_request(
                    detail_url,
                    method="GET",
                    headers=headers,
                    timeout=20,
                )
                if resp and resp.status_code == 200:
                    data = resp.json()
                    desc = data.get("jobPostingInfo", {}).get("jobDescription", "")
                    if desc:
                        job["description"] = desc
            except Exception as e:
                logger.warning(
                    f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}"
                )

        chunk_size = 10
        for i in range(0, len(jobs), chunk_size):
            chunk = jobs[i : i + chunk_size]
            await asyncio.gather(*(fetch_desc(job) for job in chunk))
            await asyncio.sleep(0.5)

        enriched = []
        for job in jobs:
            job_dict = get_job_dict(
                job_id=f"{self.site_key}_{hash(job['url'])}",
                title=job["title"],
                company=job["company"],
                location=job["location"],
                url=job["url"],
                source_url=self.base_url,
                description=job.get("description", ""),
                apply_url=job["url"],
                source=self.site_key,
            )
            enriched.append(job_dict)

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
