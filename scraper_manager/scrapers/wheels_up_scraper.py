import logging
import re
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class WheelsUpScraper(BaseScraper):
    """
    Scraper for Wheels Up (iCIMS)
    URL: https://careers-wheelsup.icims.com/jobs/search?in_iframe=1
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="wheels_up", db_manager=db_manager)
        self.base_url = "https://careers-wheelsup.icims.com/jobs/search?in_iframe=1"
        self.company_name = "Wheels Up"

    async def fetch_jobs(self) -> list:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(
                    self.base_url, wait_until="domcontentloaded", timeout=60000
                )

                # Wait for iCIMS content to load
                await page.wait_for_selector(".iCIMS_JobsTable", timeout=30000)

                page_count = 1
                while True:
                    if self.max_pages and page_count > self.max_pages:
                        break

                    logger.info(f"[{self.site_key}] Processing page {page_count}...")

                    job_rows = await page.query_selector_all(".iCIMS_JobsTable > .row")
                    if not job_rows:
                        break

                    logger.info(
                        f"[{self.site_key}] Found {len(job_rows)} job rows on page {page_count}"
                    )

                    page_jobs_data = []
                    for row in job_rows:
                        try:
                            title_el = await row.query_selector(".title a")
                            if not title_el:
                                continue

                            title = await title_el.inner_text()
                            url = await title_el.get_attribute("href")

                            # Location is usually in the header right
                            loc_el = await row.query_selector(
                                ".header.right span:not(.sr-only)"
                            )
                            location = await loc_el.inner_text() if loc_el else "USA"

                            # ID is often in a span or can be parsed from URL
                            # URL format: .../jobs/1234/job
                            match = re.search(r"/jobs/(\d+)/", url)
                            job_id = match.group(1) if match else str(hash(url))

                            page_jobs_data.append(
                                {
                                    "title": title.strip(),
                                    "url": url,
                                    "location": location.strip(),
                                    "job_id": job_id,
                                }
                            )
                        except Exception as e:
                            logger.error(f"[{self.site_key}] Error parsing row: {e}")
                            continue

                    # Process jobs
                    for job_data in page_jobs_data:
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break

                        if not self.should_process_job(job_data["title"]):
                            continue

                        if await self.is_url_already_scraped(job_data["url"]):
                            continue

                        try:
                            logger.info(
                                f"[{self.site_key}] Fetching details for: {job_data['url']}"
                            )
                            detail_page = await context.new_page()
                            # Use in_iframe=1 for detail page too if possible, or just standard
                            detail_url = job_data["url"]
                            if "?" in detail_url:
                                detail_url += "&in_iframe=1"
                            else:
                                detail_url += "?in_iframe=1"

                            await detail_page.goto(
                                detail_url, wait_until="domcontentloaded", timeout=30000
                            )
                            await detail_page.wait_for_timeout(2000)

                            # Description cleaning logic for iCIMS
                            desc_el = await detail_page.query_selector(
                                ".iCIMS_JobContent"
                            )
                            description = ""
                            if desc_el:
                                description = await desc_el.inner_text()
                            else:
                                description = await self.extract_description_from_page(
                                    detail_page
                                )

                            # Clean iCIMS noise
                            description = self.clean_icims_description(description)

                            job = get_job_dict(
                                job_id=f"wheelsup_{job_data['job_id']}",
                                title=job_data["title"],
                                company=self.company_name,
                                location=job_data["location"],
                                url=job_data["url"],
                                source_url=self.base_url,
                                description=description.strip(),
                                apply_url=job_data["url"],
                                posted_date=None,
                                source=self.site_key,
                            )

                            jobs.append(job)
                            await detail_page.close()
                            await self.random_delay(1, 3)

                        except Exception as e:
                            logger.error(
                                f"[{self.site_key}] Error fetching job detail ({job_data['url']}): {e}"
                            )
                            continue

                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    # Pagination
                    next_btn = await page.query_selector("a.iCIMS_Paginator_Next")
                    if next_btn:
                        logger.info(f"[{self.site_key}] Navigating to next page...")
                        await next_btn.click()
                        await page.wait_for_timeout(5000)
                        page_count += 1
                    else:
                        break

            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
            finally:
                await context.close()
                await browser.close()

        return jobs

    def clean_icims_description(self, text: str) -> str:
        """Remove common iCIMS boilerplate text"""
        noise_patterns = [
            r"Returning Candidate\?.*",
            r"Log back in!.*",
            r"Connect with us!.*",
            r"Introduction.*",
            r"Responsibilities.*",  # Keep if preceded by some content, but usually headers
            r"Qualifications.*",
            r"Options.*",
            r"Apply for this job onlineApply.*",
            r"Share.*",
            r"Email this job to a friendRefer.*",
            r"Sorry the Share function.*",
            r"Application FAQs.*",
            r"Software Powered by iCIMS.*",
        ]

        cleaned = text
        for pattern in noise_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.DOTALL)

        return cleaned.strip()

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        jobs = [j for j in jobs if j is not None]

        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
