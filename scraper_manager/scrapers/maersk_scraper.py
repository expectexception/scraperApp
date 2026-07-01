import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class MaerskScraper(BaseScraper):
    """
    Scraper for Maersk Careers (Workday API based, fast and stateless)
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="maersk", db_manager=db_manager)
        self.base_url = "https://maersk.wd3.myworkdayjobs.com/Maersk_Careers"
        self.api_url = "https://maersk.wd3.myworkdayjobs.com/wday/cxs/maersk/Maersk_Careers/jobs"
        self.company_name = "Maersk"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Fetching Maersk jobs via Workday API...")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # Instead of searching by keywords (which can cause Workday to return 400 Bad Request for some terms),
        # we paginate the recent job postings (e.g. first 2 pages of 100 jobs each) and filter locally.
        pages_to_fetch = 5
        limit = 20
        processed_paths = set()

        for page_idx in range(pages_to_fetch):
            offset = page_idx * limit
            logger.info(f"[{self.site_key}] Fetching page {page_idx + 1} (offset {offset})...")
            
            payload = {
                "appliedFacets": {},
                "limit": limit,
                "offset": offset,
                "searchText": ""
            }

            try:
                def make_post():
                    return requests.post(self.api_url, json=payload, headers=headers, timeout=20)
                
                resp = await asyncio.to_thread(make_post)
                if resp.status_code != 200:
                    logger.warning(f"[{self.site_key}] Failed to fetch page with status {resp.status_code}")
                    break

                data = resp.json()
                postings = data.get("jobPostings", [])
                logger.info(f"[{self.site_key}] Found {len(postings)} jobs on page {page_idx + 1}")

                if not postings:
                    break

                for p in postings:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    ext_path = p.get("externalPath")
                    if not ext_path or ext_path in processed_paths:
                        continue

                    processed_paths.add(ext_path)

                    title = p.get("title", "Unknown")
                    location = p.get("locationsText", "Unknown")
                    job_url = self.base_url + ext_path
                    job_id = "maersk_" + ext_path.split("_")[-1]

                    jobs.append({
                        "company": self.company_name,
                        "title": title,
                        "location": location,
                        "url": job_url,
                        "apply_url": job_url,
                        "source_url": self.base_url,
                        "job_id": job_id,
                        "external_path": ext_path,
                    })

            except Exception as e:
                logger.error(f"[{self.site_key}] Error fetching page {page_idx + 1}: {e}")
                break

        return jobs

    async def fetch_job_descriptions(self, jobs: list) -> list:
        if not jobs:
            return []

        logger.info(f"[{self.site_key}] Fetching descriptions for {len(jobs)} matched jobs...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }

        for job in jobs:
            ext_path = job.pop("external_path", None)
            if not ext_path:
                continue

            try:
                detail_url = f"https://maersk.wd3.myworkdayjobs.com/wday/cxs/maersk/Maersk_Careers{ext_path}"
                
                def make_get():
                    return requests.get(detail_url, headers=headers, timeout=15)

                resp = await asyncio.to_thread(make_get)
                if resp.status_code == 200:
                    data = resp.json()
                    info = data.get("jobPostingInfo", {})
                    raw_desc = info.get("jobDescription", "")
                    if raw_desc:
                        soup = BeautifulSoup(raw_desc, "html.parser")
                        job["description"] = soup.get_text(separator="\n", strip=True)
            except Exception as e:
                logger.warning(f"[{self.site_key}] Failed to fetch description for {job['title']}: {e}")

            await asyncio.sleep(0.5)

        return jobs

    async def run(self):
        self.print_header()
        jobs_raw = await self.fetch_jobs()
        jobs = [get_job_dict(**job) for job in jobs_raw]

        if not jobs:
            return []

        if self.use_filter and self.filter_manager:
            jobs, _, _ = self.apply_title_filter(jobs)
            if not jobs:
                return []

        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []

        jobs = await self.fetch_job_descriptions(jobs)
        await self.save_results(jobs)
        return jobs
