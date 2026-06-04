import asyncio
import logging
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class GridironScraper(BaseScraper):
    """
    Scraper for Gridiron Air (UltiPro)
    URL: https://recruiting2.ultipro.com/ARI1001CARD/JobBoard/952474da-aa04-4760-90e6-cdacf1e0cc13/
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="gridiron", db_manager=db_manager)
        self.base_url = "https://recruiting2.ultipro.com/ARI1001CARD/JobBoard/952474da-aa04-4760-90e6-cdacf1e0cc13/?q=&o=postedDateDesc"
        self.company_name = "Gridiron Air"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Fetching Gridiron Air jobs page...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()

            try:
                await page.goto(self.base_url, wait_until="networkidle", timeout=60000)
                await page.wait_for_selector(".opportunity", timeout=20000)
                await asyncio.sleep(2)  # Wait for Knockout.js bindings to populate

                job_items = await page.query_selector_all(".opportunity")
                logger.info(f"[{self.site_key}] Found {len(job_items)} job entries")

                for item in job_items:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    title_elem = await item.query_selector("ukg-link[data-automation='job-title']")
                    if not title_elem:
                        continue

                    title = await title_elem.inner_text()
                    title = title.strip()

                    href = await title_elem.get_attribute("href")
                    if href:
                        url = urljoin(self.base_url, href)
                    else:
                        continue

                    # Extract location using Playwright
                    loc_elem = await item.query_selector("[data-automation='job-location']")
                    location = await loc_elem.inner_text() if loc_elem else "Unknown"
                    location = location.strip()

                    # Extract job_id from url
                    job_id = url.split("/")[-1] if "/" in url else "unknown"

                    jobs.append(
                        get_job_dict(
                            job_id=job_id,
                            title=title,
                            company=self.company_name,
                            location=location,
                            url=url,
                            source_url=self.base_url,
                            description="",
                            apply_url=url,
                            source=self.site_key
                        )
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
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    html = await page.content()
                    soup = BeautifulSoup(html, "html.parser")

                    # UKG job descriptions are usually in a container like .opportunity-description
                    content = soup.find(
                        "div", class_="opportunity-description"
                    ) or soup.find("div", class_="opportunity-content")
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
