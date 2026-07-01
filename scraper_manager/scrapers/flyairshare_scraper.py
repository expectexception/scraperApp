import asyncio
import logging
import requests
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class FlyAirshareScraper(BaseScraper):
    """
    Scraper for FlyAirshare (Paycom ATS)
    URL: https://careers.flyairshare.com/career-openings/
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="flyairshare", db_manager=db_manager)
        self.base_url = "https://careers.flyairshare.com/career-openings/"
        self.company_name = "FlyAirshare"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Starting Playwright to capture Paycom API headers...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            headers_captured = {}

            async def handle_request(request):
                if "job-posting-previews/search" in request.url:
                    headers_captured.update(request.headers)

            page.on("request", handle_request)

            try:
                # Go to the career openings page which contains the Paycom iframe
                await page.goto(self.base_url, wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(3000)
            except Exception as e:
                logger.error(f"[{self.site_key}] Error loading page: {e}")

            await context.close()
            await browser.close()

        if not headers_captured:
            logger.error(f"[{self.site_key}] Failed to capture Paycom API headers.")
            return []

        logger.info(f"[{self.site_key}] Successfully captured headers. Querying Paycom API...")
        try:
            url = "https://portal-applicant-tracking.us-cent.paycomonline.net/api/ats/job-posting-previews/search"
            payload = {
                "skip": 0,
                "take": 100,
                "filtersForQuery": {
                    "distanceFrom": 0,
                    "workEnvironments": [],
                    "positionTypes": [],
                    "educationLevels": [],
                    "categories": [],
                    "travelTypes": [],
                    "shiftTypes": [],
                    "otherFilters": [],
                    "keywordSearchText": "",
                    "location": "",
                    "sortOption": ""
                }
            }

            # Filter headers
            headers = {k: v for k, v in headers_captured.items() if k.lower() not in ["host", "content-length"]}
            
            resp = requests.post(url, json=payload, headers=headers, timeout=20)
            if resp.status_code != 200:
                logger.error(f"[{self.site_key}] API query failed with status {resp.status_code}")
                return []

            data = resp.json()
            previews = data.get("jobPostingPreviews", [])
            logger.info(f"[{self.site_key}] Found {len(previews)} jobs in Paycom API")

            for p in previews:
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break

                job_id_num = p.get("jobId")
                title = p.get("jobTitle", "Unknown")
                location = p.get("locations", "Unknown")
                
                job_url = f"https://www.paycomonline.net/v4/ats/web.php/jobs?clientkey=EFB6DEFFC727A2FC82DD4522CB84EA1D&fromClientSide=true#/job-details/{job_id_num}"
                
                # Fetch description
                description = ""
                try:
                    detail_url = f"https://portal-applicant-tracking.us-cent.paycomonline.net/api/ats/job-postings/{job_id_num}"
                    detail_resp = requests.get(detail_url, headers=headers, timeout=10)
                    if detail_resp.status_code == 200:
                        detail_data = detail_resp.json()
                        raw_desc = detail_data.get("jobPosting", {}).get("description", "")
                        if raw_desc:
                            soup = BeautifulSoup(raw_desc, "html.parser")
                            description = soup.get_text(separator="\n", strip=True)
                except Exception as ex:
                    logger.warning(f"[{self.site_key}] Failed to fetch description for job {job_id_num}: {ex}")

                job = get_job_dict(
                    job_id=f"flyairshare_{job_id_num}",
                    title=title,
                    company=self.company_name,
                    location=location,
                    url=job_url,
                    source_url=self.base_url,
                    description=description,
                    apply_url=job_url,
                    source=self.site_key
                )
                jobs.append(job)

        except Exception as e:
            logger.error(f"[{self.site_key}] Error fetching jobs from API: {e}")

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

        await self.save_results(jobs)
        return jobs
