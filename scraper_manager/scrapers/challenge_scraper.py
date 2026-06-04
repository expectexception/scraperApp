import asyncio
import logging
from playwright.async_api import async_playwright
from urllib.parse import urljoin

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class ChallengeGroupScraper(BaseScraper):
    """
    Scraper for Challenge Group
    URL: https://career.challenge-group.com/search/
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="challenge", db_manager=db_manager)
        self.base_url = "https://career.challenge-group.com/search/"
        self.company_name = "Challenge Group"

    async def fetch_jobs(self) -> list:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()

            logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
            try:
                await page.goto(self.base_url, wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(5000)

                # Wait for jobs to load

                # Handle pagination or just extract the current page
                while True:
                    try:
                        await page.wait_for_selector(
                            "table#searchresults", timeout=30000
                        )
                    except:
                        logger.warning(
                            f"[{self.site_key}] Table searchresults not found."
                        )
                        break

                    rows = await page.query_selector_all(
                        "table#searchresults tbody tr.data-row"
                    )
                    if not rows:
                        break

                    logger.info(
                        f"[{self.site_key}] Found {len(rows)} jobs on this page"
                    )

                    for row in rows:
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break

                        link = await row.query_selector("a.jobTitle-link")
                        if not link:
                            continue

                        title = await link.inner_text()
                        title = title.strip()
                        href = await link.get_attribute("href")
                        url = urljoin(self.base_url, href)

                        location_elem = await row.query_selector("span.jobLocation")
                        location = (
                            await location_elem.inner_text()
                            if location_elem
                            else "Unknown"
                        )
                        location = location.strip().replace("\n", " ")

                        job_id = (
                            url.split("/")[-2]
                            if len(url.split("/")) > 2
                            else str(hash(url))
                        )

                        jobs.append(
                            {
                                "company": self.company_name,
                                "title": title,
                                "location": location,
                                "url": url,
                                "source_url": self.base_url,
                                "apply_url": url,
                                "is_active": True,
                                "job_seq_no": job_id,
                            }
                        )

                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    # Next page
                    next_link = await page.query_selector("a.next-page")
                    if next_link and await next_link.is_visible():
                        await next_link.click()
                        await page.wait_for_timeout(2000)
                    else:
                        break

            except Exception as e:
                logger.error(f"[{self.site_key}] Error fetching jobs: {e}")

            finally:
                await context.close()
                await browser.close()

        return jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        if not jobs:
            return []

        logger.info(
            f"[{self.site_key}] Fetching descriptions for {len(jobs)} matched jobs..."
        )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            for job in jobs:
                url = job["url"]
                try:
                    await page.goto(url, wait_until="networkidle", timeout=20000)
                    desc_elem = await page.query_selector(
                        "div.jobdescription"
                    ) or await page.query_selector("span.jobdescription")
                    if desc_elem:
                        job["description"] = await desc_elem.inner_text()
                except Exception as e:
                    logger.warning(
                        f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}"
                    )

                await asyncio.sleep(0.5)

            await context.close()
            await browser.close()

        return jobs

    async def run(self):
        self.print_header()

        jobs = await self.fetch_jobs()
        if not jobs:
            return []

        if self.use_filter and self.filter_manager:
            logger.info(f"[{self.site_key}] Applying filter...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []

        jobs = await self.fetch_job_descriptions(jobs)
        await self.save_results(jobs)
        return jobs
