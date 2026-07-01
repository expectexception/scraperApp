import asyncio
import logging
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class EndeavorScraper(BaseScraper):
    """
    Scraper for Endeavor Air (iCIMS)
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="endeavor", db_manager=db_manager)
        self.base_url = "https://careers-endeavorair.icims.com/jobs/search?in_iframe=1"
        self.company_name = "Endeavor Air"

    async def fetch_jobs(self) -> list:
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(5000)

                # Find the frame containing the jobs table
                target_frame = page
                for f in page.frames:
                    try:
                        if await f.query_selector(".iCIMS_JobsTable"):
                            target_frame = f
                            logger.info(f"[{self.site_key}] Found jobs table in frame: {f.url}")
                            break
                    except Exception:
                        pass

                job_rows = await target_frame.locator(".iCIMS_JobsTable .row, .iCIMS_JobListing").all()
                logger.info(f"[{self.site_key}] Found {len(job_rows)} job rows in iCIMS")

                for row in job_rows:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                    try:
                        title_el = row.locator("div.title a.iCIMS_Anchor, a.iCIMS_JobListingLink").first
                        if not await title_el.is_visible():
                            continue
                        title = await title_el.inner_text()
                        if "Requisition Title" in title:
                            title = title.replace("Requisition Title", "")
                        title = title.strip()
                        
                        url = await title_el.get_attribute("href")
                        if url and "?" in url:
                            url = url.split("?")[0]
                        if url and not url.startswith("http"):
                            url = "https://careers-endeavorair.icims.com" + url

                        location = "USA"
                        loc_el = row.locator(".header.left span:not(.sr-only), .location span:nth-child(2)").first
                        if await loc_el.is_visible():
                            location = await loc_el.inner_text()

                        job_id = "endeavor_" + str(hash(url))

                        jobs.append({
                            "company": self.company_name,
                            "title": title.strip(),
                            "location": location.strip(),
                            "url": url,
                            "apply_url": url,
                            "source_url": self.base_url,
                            "job_id": job_id,
                            "description": "",
                        })
                    except Exception as e:
                        logger.warning(f"[{self.site_key}] Error parsing row: {e}")
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

                    # Find the frame containing the job description
                    target_frame = page
                    for f in page.frames:
                        try:
                            if await f.query_selector(".iCIMS_JobDescription"):
                                target_frame = f
                                break
                        except Exception:
                            pass

                    desc_text = ""
                    selectors = [".iCIMS_JobDescription", ".job-description", ".content", "main"]
                    for sel in selectors:
                        el = target_frame.locator(sel).first
                        if await el.is_visible():
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
