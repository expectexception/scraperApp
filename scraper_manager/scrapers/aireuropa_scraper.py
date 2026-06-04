import asyncio
import logging
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class AirEuropaScraper(BaseScraper):
    """
    Scraper for Air Europa
    URL: https://vacantes.aireuropa.com/jobs
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="aireuropa", db_manager=db_manager)
        self.base_url = "https://vacantes.aireuropa.com/jobs"
        self.company_name = "Air Europa"

    async def fetch_jobs(self) -> list:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
            try:
                await page.goto(self.base_url, wait_until="networkidle", timeout=30000)

                # Check for "Load more" button to get all jobs if it's paginated
                while True:
                    load_more = await page.query_selector(
                        'button:has-text("Load more"), button:has-text("Cargar más")'
                    )
                    if load_more and await load_more.is_visible():
                        await load_more.click()
                        await page.wait_for_timeout(2000)
                    else:
                        break

                links = await page.query_selector_all('a[href*="/jobs/"]')
                logger.info(f"[{self.site_key}] Found {len(links)} links")

                processed_urls = set()

                for a in links:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    href = await a.get_attribute("href")
                    if not href or href == "/jobs" or href in processed_urls:
                        continue

                    url = (
                        href
                        if href.startswith("http")
                        else f"https://vacantes.aireuropa.com{href}"
                    )
                    processed_urls.add(href)

                    # title is inside the link, or the link is just a card
                    # extract the title from the card
                    title_elem = await a.query_selector("span.text-block-base-link")
                    title = (
                        await title_elem.inner_text()
                        if title_elem
                        else await a.inner_text()
                    )
                    title = title.split("\n")[0].strip()

                    if not self.should_process_job(title):
                        continue

                    # find location if available
                    loc_elem = await a.query_selector(
                        "div.mt-1 span, div.flex.items-center span"
                    )
                    location = await loc_elem.inner_text() if loc_elem else "Spain"

                    job_id = url.split("/")[-1]

                    jobs.append(
                        get_job_dict(
                            job_id=job_id,
                            title=title,
                            company=self.company_name,
                            location=location.strip(),
                            url=url,
                            source_url=self.base_url,
                            apply_url=url,
                            description="",
                            source=self.site_key,
                        )
                    )
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
            page, context = await self.setup_stealth_page(browser)

            for job in jobs:
                url = job["url"]
                try:
                    await page.goto(url, wait_until="networkidle", timeout=20000)
                    desc_elem = await page.query_selector(
                        "main, .job-description, .content, article"
                    )
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
