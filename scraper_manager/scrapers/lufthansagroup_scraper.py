import logging
import asyncio
from typing import List, Dict
from urllib.parse import urljoin
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class LufthansagroupScraper(BaseScraper):
    """
    Scraper for Lufthansa Group Careers using Playwright.
    URL: https://apply.lufthansagroup.careers/index.php?ac=search_result&search_criterion_channel%5B%5D=12&language=2
    """

    def __init__(self, config: Dict, db_manager=None):
        super().__init__(config, site_key="lufthansagroup", db_manager=db_manager)
        self.base_url = "https://apply.lufthansagroup.careers/index.php?ac=search_result&search_criterion_channel%5B%5D=12&language=2"
        self.company_name = "Lufthansa Group"

    async def fetch_jobs(self) -> List[Dict]:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
                try:
                    await page.wait_for_selector('a.jobad-link-wrapper', timeout=20000)
                except Exception:
                    logger.warning(f"[{self.site_key}] job listing selector did not appear within timeout, proceeding anyway.")
                await page.wait_for_timeout(2000)

                # The rexx-systems portal renders each posting as
                # <a class="jobad-link-wrapper" href="...ac=jobad&id=..."><td data-jobad-title="..."> ... </td></a>
                # The visible inner_text() of the wrapper is empty (content is laid out via CSS),
                # so the title must be read from the data-jobad-title attribute instead.
                job_elements = await page.query_selector_all('a.jobad-link-wrapper')

                # The portal occasionally still renders the result list a beat after the
                # selector wait above resolves (slow XHR under load). Retry briefly rather
                # than silently reporting 0 jobs.
                retries = 0
                while not job_elements and retries < 3:
                    retries += 1
                    logger.warning(f"[{self.site_key}] No job elements yet, retrying ({retries}/3)...")
                    await page.wait_for_timeout(3000)
                    job_elements = await page.query_selector_all('a.jobad-link-wrapper')

                logger.info(f"[{self.site_key}] Found {len(job_elements)} job elements.")

                for el in job_elements:
                    href = await el.get_attribute("href")
                    title = await el.evaluate(
                        "el => { const t = el.querySelector('[data-jobad-title]'); "
                        "return t ? t.getAttribute('data-jobad-title') : null; }"
                    )
                    title = (title or "").strip()

                    if not href or not title:
                        continue

                    job_url = urljoin(self.base_url, href)
                    
                    if not self.should_process_job(title):
                        continue

                    job_id = f"{self.site_key}_{hash(job_url)}"
                    
                    job = get_job_dict(
                        job_id=job_id,
                        title=title,
                        company=self.company_name,
                        location="Unknown",
                        url=job_url,
                        source_url=self.base_url,
                        description="Lufthansa Group Career Opportunity.",
                        apply_url=job_url,
                        source=self.site_key
                    )
                    
                    jobs.append(job)

                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                return jobs

            except Exception as e:
                logger.error(f"[{self.site_key}] Error scraping: {e}")
                return jobs
            finally:
                await browser.close()

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
