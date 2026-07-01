import asyncio
import logging
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

JOBS_LIST_URL = "https://magnifica-air.oasisrecruit.com"
BASE_URL = "https://magnificaair.com/careers/"


class MagnificaAirScraper(BaseScraper):
    """
    Scraper for Magnifica Air (Paychex/oasisrecruit ATS)
    Jobs are on: https://magnifica-air.oasisrecruit.com
    Main careers page: https://magnificaair.com/careers/
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="magnificaair", db_manager=db_manager)
        self.base_url = BASE_URL
        self.company_name = "Magnifica Air"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Scraping Magnifica Air job listings...")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        try:
            resp = await self.make_request(
                JOBS_LIST_URL, method="GET", headers=headers, timeout=20
            )
            if not resp or resp.status_code != 200:
                logger.warning(
                    f"[{self.site_key}] Failed to fetch job list: {resp.status_code if resp else 'None'}"
                )
                return jobs

            soup = BeautifulSoup(resp.text, "html.parser")
            containers = soup.select(".job-container")

            for container in containers:
                link_el = container.select_one("a.mobile-apply-link")
                if not link_el:
                    continue

                href = link_el.get("href", "")
                job_url = f"{JOBS_LIST_URL}{href}" if href.startswith("/") else href

                title_el = link_el.select_one("h2")
                title = title_el.get_text(strip=True) if title_el else "Unknown"

                loc_el = container.select_one(".job-location")
                location = loc_el.get_text(strip=True) if loc_el else "Unknown"

                cat_el = container.select_one(".job-category span")
                category = cat_el.get_text(strip=True) if cat_el else ""

                jobs.append(
                    {
                        "company": self.company_name,
                        "title": title,
                        "location": location,
                        "url": job_url,
                        "source_url": job_url,
                        "apply_url": job_url,
                        "is_active": True,
                        "description": category,
                    }
                )

        except Exception as e:
            logger.error(f"[{self.site_key}] Failed to fetch job list: {e}")

        logger.info(f"[{self.site_key}] Found {len(jobs)} jobs")
        return jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        if not jobs:
            return []

        logger.info(
            f"[{self.site_key}] Fetching full descriptions for {len(jobs)} jobs..."
        )
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        async def fetch_detail(job):
            try:
                resp = await self.make_request(
                    job["url"], method="GET", headers=headers, timeout=15
                )
                if resp and resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    content = soup.select_one(".job-content-body, .job-content, .job-description, main, #job-details")
                    if content:
                        job["description"] = content.get_text(" ", strip=True)[:5000]
            except Exception as e:
                logger.warning(
                    f"[{self.site_key}] Failed to get detail for {job['title']}: {e}"
                )

        chunk_size = 5
        for i in range(0, len(jobs), chunk_size):
            chunk = jobs[i : i + chunk_size]
            await asyncio.gather(*(fetch_detail(job) for job in chunk))
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
