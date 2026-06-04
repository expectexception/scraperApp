import logging
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class BraathensScraper(BaseScraper):
    """
    Scraper for Braathens Regional Airlines
    Uses HR Manager API
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="braathens", db_manager=db_manager)
        self.base_url = "https://www.braathens.com/career/"
        self.api_url = "https://recruiter-api.hr-manager.net/jobportal.svc/braathens/positionlist/json/?mediaid=4615&take=20&sortby=Created&sortasc=0"
        self.company_name = "Braathens Regional Airlines"

    async def fetch_jobs(self) -> list:
        jobs = []
        try:
            logger.info(f"[{self.site_key}] Fetching from API: {self.api_url}")
            resp = await self.make_request(self.api_url)
            data = resp.json()

            items = data.get("Items", [])
            logger.info(f"[{self.site_key}] Found {len(items)} jobs in API")

            for i, item in enumerate(items):
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break

                job_id = str(item.get("Id", ""))
                title = item.get("Name", "")

                # Fetch details page to get description
                url = f"https://www.braathens.com/career/?rmpage=job&rmjob={job_id}"

                # Skip duplicate URLs
                if await self.is_url_already_scraped(url):
                    continue

                if not self.is_job_link(title, url):
                    continue

                if not self.should_process_job(title):
                    continue

                if await self.is_url_already_scraped(url):
                    continue

                logger.info(f"[{self.site_key}] Fetching details for: {url}")

                try:
                    detail_resp = await self.make_request(url)
                    detail_html = detail_resp.text
                    soup = BeautifulSoup(detail_html, "html.parser")

                    description = ""
                    desc_elem = soup.select_one(
                        ".job-description, .content, article, main, .tm-jobad-content"
                    )
                    if desc_elem:
                        description = desc_elem.get_text(separator="\\n", strip=True)
                    else:
                        description = detail_html[:1000]  # Fallback just in case

                    posted_date = None  # Could parse from API if available

                    job = get_job_dict(
                        job_id=f"braathens_{job_id}",
                        title=title,
                        company=self.company_name,
                        location="Sweden",
                        url=url,
                        source_url=url,
                        description=description,
                        apply_url=url,
                        posted_date=posted_date,
                        source=self.site_key,
                    )
                    jobs.append(job)

                    await self.random_delay()

                except Exception as e:
                    logger.error(
                        f"[{self.site_key}] Error getting details for {url}: {e}"
                    )

        except Exception as e:
            logger.error(f"[{self.site_key}] API request failed: {e}")

        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()

        # Apply filter before saving
        matched_jobs, rejected_jobs, stats = self.apply_title_filter(jobs)

        await self.save_results(matched_jobs)
        return matched_jobs
