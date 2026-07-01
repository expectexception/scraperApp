import asyncio
import logging
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class AlaskaScraper(BaseScraper):
    """
    Scraper for Alaska Airlines (focusing on Airport Operations category)
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="alaska", db_manager=db_manager)
        self.base_url = "https://careers.alaskaair.com/job-category/airport-operations/jobs/"
        self.company_name = "Alaska Airlines"

    async def fetch_jobs(self) -> list:
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(5000)

                job_links = await page.query_selector_all('a[href*="/job/"]')
                logger.info(f"[{self.site_key}] Found {len(job_links)} total links matching /job/")

                for link in job_links:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                    try:
                        title_el = await link.query_selector("div.job h2, h2")
                        if not title_el:
                            continue
                        title = (await title_el.inner_text()).strip()

                        url = await link.get_attribute("href")
                        if url and not url.startswith("http"):
                            url = "https://careers.alaskaair.com" + url

                        # Avoid duplicates
                        if any(j["url"] == url for j in jobs):
                            continue

                        location = "USA"
                        loc_el = await link.query_selector("div.job > div:nth-of-type(1), .job-location")
                        if loc_el:
                            loc_text = (await loc_el.inner_text()).strip()
                            if loc_text:
                                location = loc_text

                        job_id = "alaska_" + str(hash(url))

                        jobs.append({
                            "company": self.company_name,
                            "title": title,
                            "location": location,
                            "url": url,
                            "apply_url": url,
                            "source_url": self.base_url,
                            "job_id": job_id,
                            "description": "",
                        })
                    except Exception as e:
                        logger.warning(f"[{self.site_key}] Error parsing job link: {e}")
            except Exception as e:
                logger.error(f"[{self.site_key}] Error: {e}")
            finally:
                await context.close()
                await browser.close()

        return jobs

    async def fetch_job_descriptions(self, jobs: list) -> list:
        if not jobs:
            return []

        logger.info(f"[{self.site_key}] Fetching descriptions for {len(jobs)} matched jobs...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            for job in jobs:
                try:
                    logger.info(f"[{self.site_key}] Fetching details for {job['title']}...")
                    await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(2000)

                    # Extract description
                    desc_text = ""
                    selectors = [".job-description", ".description", "main", "#job-details"]
                    for sel in selectors:
                        el = await page.query_selector(sel)
                        if el:
                            desc_text = (await el.inner_text()).strip()
                            if len(desc_text) > 100:
                                break

                    if not desc_text:
                        desc_text = await self.extract_description_from_page(page)

                    job["description"] = desc_text

                except Exception as e:
                    logger.warning(f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}")

            await context.close()
            await browser.close()

        return jobs

    async def run(self):
        self.print_header()
        jobs_raw = await self.fetch_jobs()
        jobs = [get_job_dict(**job) for job in jobs_raw]

        if not jobs:
            return []

        if self.use_filter and self.filter_manager:
            jobs, _, _ = self.apply_title_filter(jobs)
            if not jobs:
                return []

        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []

        jobs = await self.fetch_job_descriptions(jobs)
        await self.save_results(jobs)
        return jobs
