import logging
import re
from datetime import datetime
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class AirwaysScraper(BaseScraper):
    """
    Scraper for Airways New Zealand Career Centre
    URL: https://airways.careercentre.net.nz/job
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="airways", db_manager=db_manager)
        self.base_url = "https://airways.careercentre.net.nz"
        self.jobs_url = "https://airways.careercentre.net.nz/job"
        self.company_name = "Airways"

    async def fetch_jobs(self) -> list:
        jobs = []
        try:
            logger.info(f"[{self.site_key}] Fetching list page: {self.jobs_url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            resp = await self.make_request(self.jobs_url, headers=headers)
            if not resp or resp.status_code != 200:
                logger.error(
                    f"[{self.site_key}] Failed to fetch list page: Status {resp.status_code if resp else 'None'}"
                )
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select(".vacancy-item")
            logger.info(f"[{self.site_key}] Found {len(items)} jobs in list page")

            for item in items:
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break

                title_el = item.select_one("h2 a, h3 a")
                if not title_el:
                    continue

                title = title_el.text.strip()
                path = title_el.get("href", "")
                if not path:
                    continue

                url = self.base_url + path if path.startswith("/") else path

                # Extract location
                location = "New Zealand"
                for fg in item.select(".form-group"):
                    strong = fg.select_one("strong")
                    if strong and "Location" in strong.text:
                        span = fg.select_one("span")
                        if span:
                            location = span.text.strip()
                        break

                # Extract closing date
                closing_date_str = ""
                for fg in item.select(".form-group"):
                    strong = fg.select_one("strong")
                    if strong and "Closing date" in strong.text:
                        span = fg.select_one("span")
                        if span:
                            closing_date_str = span.text.strip()
                        break

                job_id = f"airways_{abs(hash(url)) % 10000000}"

                jobs.append(
                    {
                        "job_id": job_id,
                        "title": title,
                        "company": self.company_name,
                        "source": self.site_key,
                        "url": url,
                        "apply_url": url,
                        "location": location,
                        "timestamp": datetime.now().isoformat(),
                        "description": "",
                    }
                )

        except Exception as e:
            logger.error(f"[{self.site_key}] Error fetching jobs: {e}")

        return jobs

    async def fetch_job_descriptions(self, jobs: list) -> list:
        if not jobs:
            return jobs

        logger.info(f"[{self.site_key}] Fetching descriptions for {len(jobs)} jobs...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        for job in jobs:
            try:
                url = job["url"]
                resp = await self.make_request(url, headers=headers)
                if resp and resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    desc_div = soup.select_one(".job-ad-body")
                    if desc_div:
                        job["description"] = desc_div.get_text(
                            separator="\n", strip=True
                        )
                    else:
                        job["description"] = await self.extract_description_from_page(
                            None, soup
                        )

            except Exception as e:
                logger.warning(
                    f"[{self.site_key}] Failed to fetch description for {job['url']}: {e}"
                )

        return jobs

    async def run(self):
        self.print_header()
        jobs_raw = await self.fetch_jobs()
        jobs = [get_job_dict(**job) for job in jobs_raw]

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
