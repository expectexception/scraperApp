import logging
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class AlaskaScraper(BaseScraper):
    """
    Scraper for Alaska Airlines (iCIMS)
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="alaska", db_manager=db_manager)
        # NOTE: old "/jobs/search?in_iframe=1" iCIMS iframe URL 404s as of 2026-06.
        # Alaska's careers site migrated to a direct (non-iframe) listing page.
        self.base_url = "https://careers.alaskaair.com/company/alaska-airlines/jobs/"
        self.company_name = "Alaska Airlines"

    async def fetch_jobs(self) -> list:
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                await page.goto(
                    self.base_url, wait_until="domcontentloaded", timeout=60000
                )
                await page.wait_for_timeout(5000)

                job_links = await page.query_selector_all('a[href*="/job/"]')
                for link in job_links:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                    try:
                        title_el = await link.query_selector("div.job h2")
                        if not title_el:
                            continue
                        title = (await title_el.inner_text()).strip()

                        url = await link.get_attribute("href")
                        if url and not url.startswith("http"):
                            url = "https://careers.alaskaair.com" + url

                        location = "USA"
                        loc_el = await link.query_selector("div.job > div:nth-of-type(1)")
                        if loc_el:
                            loc_text = (await loc_el.inner_text()).strip()
                            if loc_text:
                                location = loc_text

                        job_id = "alaska_" + str(hash(url))

                        jobs.append(
                            {
                                "company": self.company_name,
                                "title": title,
                                "location": location,
                                "url": url,
                                "apply_url": url,
                                "source_url": self.base_url,
                                "job_id": job_id,
                                "description": "",
                            }
                        )
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"[{self.site_key}] Error: {e}")
            finally:
                await context.close()
                await browser.close()

        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        if self.use_filter and self.filter_manager and jobs:
            jobs, _, _ = self.apply_title_filter(jobs)
        await self.save_results(jobs)
        return jobs
