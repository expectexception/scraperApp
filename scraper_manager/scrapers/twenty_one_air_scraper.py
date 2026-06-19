import asyncio
import logging
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class TwentyOneAirScraper(BaseScraper):
    """
    Scraper for 21 Air LLC (Paylocity)
    URL: https://recruiting.paylocity.com/recruiting/jobs/All/bf3ab0f0-77a0-4342-8ff8-83069b83bd23/21-AIR-LLC
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="twenty_one_air", db_manager=db_manager)
        self.base_url = "https://recruiting.paylocity.com/recruiting/jobs/All/bf3ab0f0-77a0-4342-8ff8-83069b83bd23/21-AIR-LLC"
        self.company_name = "21 Air"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Fetching 21 Air jobs page...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()

            try:
                await page.goto(self.base_url, wait_until="networkidle", timeout=60000)
                await page.wait_for_selector(".job-listing-job-item", timeout=20000)

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")

                job_items = soup.find_all("div", class_="job-listing-job-item")
                logger.info(f"[{self.site_key}] Found {len(job_items)} job entries")

                for item in job_items:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    title_elem = item.find("a", class_="custom-link-color")
                    if not title_elem:
                        continue

                    title = title_elem.text.strip()
                    href = title_elem.get("href")
                    if href:
                        url = urljoin(self.base_url, href)
                    else:
                        continue

                    # Extract location
                    loc_elem = item.find("div", class_="location-column")
                    location = loc_elem.text.strip() if loc_elem else "Unknown"

                    # Extract job_id from url
                    job_id = url.split("/")[-1]

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

            except Exception as e:
                logger.error(f"[{self.site_key}] Error fetching jobs: {e}")
            finally:
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
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(2)
                    html = await page.content()
                    soup = BeautifulSoup(html, "html.parser")

                    content = (
                        soup.find("div", class_="job-preview-container")
                        or soup.find("div", class_="job-details-content")
                        or soup.find("body")
                    )
                    if content:
                        text = content.text
                        import re

                        text = re.sub(r"\s+", " ", text).strip()
                        job["description"] = text
                except Exception as e:
                    logger.warning(
                        f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}"
                    )

            await browser.close()

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
