import asyncio
import logging
import json

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class USAJetScraper(BaseScraper):
    """
    Scraper for USA Jet (Workday)
    URL: https://ascentgl.wd1.myworkdayjobs.com/USJ
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="usajet", db_manager=db_manager)
        self.base_url = "https://ascentgl.wd1.myworkdayjobs.com/en-US/USJ"
        self.company_name = "USA Jet"
        self.api_url = "https://ascentgl.wd1.myworkdayjobs.com/wday/cxs/ascentgl/USJ/jobs"
        self.detail_api_url = "https://ascentgl.wd1.myworkdayjobs.com/wday/cxs/ascentgl/USJ"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(
            f"[{self.site_key}] Querying Workday API endpoint directly for jobs..."
        )

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        limit = 20
        offset = 0

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
                    timeout=20
                )
                if not resp or resp.status_code != 200:
                    logger.warning(f"[{self.site_key}] API extraction failed with status {resp.status_code if resp else 'None'}")
                    break
                    
                data = resp.json()

                postings = data.get("jobPostings", [])
                if not postings:
                    break

                for j in postings:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    external_path = j.get("externalPath", "")
                    url = f"{self.base_url.rstrip('/')}{external_path}"

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

        return jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        if not jobs:
            return []

        logger.info(
            f"[{self.site_key}] Fetching descriptions for {len(jobs)} matched jobs via API..."
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
                    timeout=20
                )
                if resp and resp.status_code == 200:
                    data = resp.json()
                    desc = data.get("jobPostingInfo", {}).get("jobDescription", "")
                    if desc:
                        job["description"] = self.clean_html(desc)
            except Exception as e:
                logger.warning(
                    f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}"
                )

        chunk_size = 10
        for i in range(0, len(jobs), chunk_size):
            chunk = jobs[i:i+chunk_size]
            await asyncio.gather(*(fetch_desc(job) for job in chunk))
            await asyncio.sleep(0.5)

        return jobs

    def clean_html(self, html_content: str) -> str:
        if not html_content:
            return ""
        # Remove simple HTML tags
        import re
        import html as html_lib
        clean = html_lib.unescape(html_content)
        clean = re.sub(r"<[^>]*>", " ", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
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
        
        final_jobs = []
        for j in jobs:
            # Generate job ID from title/location to be safe and clean
            job_id = f"usajet_{hash(j['url'])}"
            final_jobs.append(
                get_job_dict(
                    job_id=job_id,
                    title=j["title"],
                    company=self.company_name,
                    location=j["location"],
                    url=j["url"],
                    source_url=j["url"],
                    description=j.get("description", ""),
                    apply_url=j["apply_url"],
                    source=self.site_key,
                )
            )

        await self.save_results(final_jobs)
        return final_jobs
