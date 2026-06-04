import logging
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class FAIScraper(BaseScraper):
    """
    Scraper for FAI Aviation Group
    URL: https://www.fai.ag/career/job-offers
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="fai", db_manager=db_manager)
        self.base_url = "https://www.fai.ag/career/job-offers"
        self.company_name = "FAI Aviation Group"
        self.job_categories = [
            "flight-operations",
            "air-ambulance",
            "aircraft-maintenance-and-logitics",
            "other-positions",
        ]

    async def fetch_jobs(self) -> list:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            for category in self.job_categories:
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break

                cat_url = f"{self.base_url}/{category}/"
                logger.info(f"[{self.site_key}] Navigating to {cat_url}...")

                try:
                    await page.goto(cat_url, wait_until="networkidle", timeout=30000)

                    # Accept cookies if present
                    try:
                        await page.click(
                            'button:has-text("Accept"), button:has-text("Zustimmen")',
                            timeout=3000,
                        )
                    except:
                        pass

                    items = await page.query_selector_all(".accordion-item")
                    logger.info(
                        f"[{self.site_key}] Found {len(items)} jobs in {category}"
                    )

                    for i, item in enumerate(items):
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break

                        try:
                            # Extract title
                            title_el = await item.query_selector(
                                ".accordion-trigger span:first-child"
                            )
                            if not title_el:
                                continue
                            title = await title_el.inner_text()
                            title = title.strip()

                            if not self.should_process_job(title):
                                continue

                            # Click to open accordion and read description
                            trigger = await item.query_selector(".accordion-trigger")
                            if trigger:
                                await trigger.click()
                                await page.wait_for_timeout(
                                    1000
                                )  # Wait for animation/render

                            desc_el = await item.query_selector(".accordion-content")
                            description = await desc_el.inner_text() if desc_el else ""

                            job_id = f"fai_{category}_{i}"

                            jobs.append(
                                get_job_dict(
                                    job_id=job_id,
                                    title=title,
                                    company=self.company_name,
                                    location="Nuremberg, Germany",  # FAI HQ
                                    url=cat_url,
                                    source_url=cat_url,
                                    apply_url="mailto:career@fai.ag",  # From the page
                                    description=description.strip(),
                                    source=self.site_key,
                                )
                            )
                        except Exception as e:
                            logger.error(
                                f"[{self.site_key}] Error parsing job in {category}: {e}"
                            )

                except Exception as e:
                    logger.error(f"[{self.site_key}] Failed to load {category}: {e}")

            await context.close()
            await browser.close()

        return jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        # Descriptions are already fetched in fetch_jobs due to accordion structure
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

        await self.save_results(jobs)
        return jobs
