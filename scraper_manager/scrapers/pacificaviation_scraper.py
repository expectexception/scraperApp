import asyncio
import logging
import requests

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class PacificAviationScraper(BaseScraper):
    """
    Scraper for Pacific Aviation
    URL: https://apply.workable.com/pacificaviation/?lng=en
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="pacificaviation", db_manager=db_manager)
        self.base_url = "https://apply.workable.com/pacificaviation/?lng=en"
        self.api_url = "https://apply.workable.com/api/v3/accounts/pacificaviation/jobs"
        self.company_name = "Pacific Aviation"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(
            f"[{self.site_key}] Querying Workable API directly for Pacific Aviation jobs..."
        )

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        payload = {
            "query": "",
            "location": [],
            "department": [],
            "worktype": [],
            "remote": [],
        }

        try:
            resp = requests.post(
                self.api_url, json=payload, headers=headers, timeout=20
            )
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", [])
            logger.info(f"[{self.site_key}] API returned {len(results)} jobs")

            for j in results:
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break

                title = j.get("title", "Unknown")
                shortcode = j.get("shortcode", "")
                if not shortcode:
                    continue

                url = f"https://apply.workable.com/pacificaviation/j/{shortcode}/"

                # Try to extract location
                loc_dict = j.get("location", {})
                loc_str = "Unknown"
                if loc_dict:
                    city = loc_dict.get("city", "")
                    country = loc_dict.get("countryName", "")
                    loc_parts = [p for p in [city, country] if p]
                    if loc_parts:
                        loc_str = ", ".join(loc_parts)

                jobs.append(
                    {
                        "company": self.company_name,
                        "title": title,
                        "location": loc_str,
                        "url": url,
                        "source_url": self.base_url,
                        "apply_url": url,
                        "is_active": True,
                        "job_seq_no": shortcode,
                    }
                )
        except Exception as e:
            logger.error(f"[{self.site_key}] Error fetching jobs via API: {e}")

        return jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        if not jobs:
            return []

        logger.info(
            f"[{self.site_key}] Fetching descriptions for {len(jobs)} matched jobs via API..."
        )

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json",
        }

        for job in jobs:
            shortcode = job.pop("job_seq_no", None)
            if not shortcode:
                continue

            try:
                # Workable has a specific endpoint for job details
                detail_url = f"https://apply.workable.com/api/v1/jobs/{shortcode}"
                resp = requests.get(detail_url, headers=headers, timeout=20)
                if resp.status_code == 200:
                    data = resp.json()
                    desc = data.get("description", "")
                    import re

                    # Remove HTML tags using a simple regex since it's an API response
                    clean_desc = re.sub(r"<[^>]+>", " ", desc)
                    clean_desc = re.sub(r"\s+", " ", clean_desc).strip()
                    if clean_desc:
                        job["description"] = clean_desc
            except Exception as e:
                logger.warning(
                    f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}"
                )

            await asyncio.sleep(0.5)

        return jobs

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
        await self.save_results(jobs)
        return jobs
