import logging
import re
from datetime import datetime
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class CutterScraper(BaseScraper):
    """
    Scraper for Cutter Aviation (Paylocity Feed API)
    URL: https://cutteraviation.com/careers/
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="cutter", db_manager=db_manager)
        self.base_url = "https://cutteraviation.com/careers/"
        self.api_url = "https://recruiting.paylocity.com/recruiting/v2/api/feed/jobs/e31122d0-2189-4eb9-8b32-a8dd1dafea6c"
        self.company_name = "Cutter Aviation"

    async def fetch_jobs(self) -> list:
        all_jobs = []
        logger.info(f"[{self.site_key}] Fetching from API: {self.api_url}")

        try:
            resp = await self.make_request(self.api_url)
            if not resp or resp.status_code != 200:
                logger.error(
                    f"[{self.site_key}] Failed to fetch jobs: Status {resp.status_code if resp else 'None'}"
                )
                return []

            data = resp.json()
            job_list = data.get("jobs", [])
            logger.info(f"[{self.site_key}] Found {len(job_list)} jobs in feed")

            for j in job_list:
                if self.max_jobs and len(all_jobs) >= self.max_jobs:
                    break

                job_id = f"cutter_{j.get('jobId')}"
                title = j.get("title", "").strip()
                apply_url = j.get("applyUrl", "")
                display_url = j.get("displayUrl", apply_url)

                # Parse location
                loc_obj = j.get("jobLocation", {})
                city = loc_obj.get("city", "")
                state = loc_obj.get("state", "")
                location = f"{city}, {state}".strip(", ")
                if not location:
                    location = "Global"

                # Combine description and requirements
                desc_html = j.get("description", "")
                req_html = j.get("requirements", "")
                description = self.clean_html(desc_html + "\n" + req_html)

                # Parse posted date
                pub_date = j.get("publishedDate")
                posted_date = None
                if pub_date:
                    try:
                        # e.g., 2026-06-17T15:28:23Z
                        posted_date = datetime.strptime(
                            pub_date.split(".")[0].rstrip("Z"), "%Y-%m-%dT%H:%M:%S"
                        )
                    except Exception:
                        pass

                job = get_job_dict(
                    job_id=job_id,
                    title=title,
                    company=self.company_name,
                    location=location,
                    url=display_url,
                    source_url=self.base_url,
                    description=description,
                    apply_url=apply_url,
                    posted_date=posted_date,
                    source=self.site_key,
                )
                all_jobs.append(job)

        except Exception as e:
            logger.error(f"[{self.site_key}] Global error: {e}")

        return all_jobs

    def clean_html(self, html_content: str) -> str:
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text(separator="\n")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        jobs = [j for j in jobs if j is not None]

        if self.use_filter and self.filter_manager and jobs:
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
