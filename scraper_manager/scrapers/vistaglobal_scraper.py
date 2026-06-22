import logging
import asyncio
from typing import List, Dict
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class VistaGlobalScraper(BaseScraper):
    """
    Scraper for Vista Global (iCIMS) via Playwright.
    URL: https://hub-vistaglobal.icims.com/jobs/search?ss=1
    """

    def __init__(self, config: Dict, db_manager=None):
        super().__init__(config, site_key="vistaglobal", db_manager=db_manager)
        self.site_config = config.get("sites", {}).get("vistaglobal", {})
        self.base_url = self.site_config.get("jobs_url", "https://hub-vistaglobal.icims.com/jobs/search?ss=1&in_iframe=1")
        self.company_name = "Vista Global"

    async def fetch_jobs(self) -> List[Dict]:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                page_num = 0
                while True:
                    url = f"{self.base_url}&pr={page_num}"
                    logger.info(f"[{self.site_key}] Navigating to {url}...")
                    
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    
                    # Try waiting for the jobs table
                    try:
                        await page.wait_for_selector('.iCIMS_JobsTable .row', timeout=15000)
                    except:
                        logger.warning(f"[{self.site_key}] Timeout waiting for job cards, assuming end of pagination.")
                        break

                    html = await page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    rows = soup.select('.iCIMS_JobsTable .row')

                    if not rows:
                        break
                        
                    logger.info(f"[{self.site_key}] Found {len(rows)} job cards on page {page_num}")

                    added_on_page = 0
                    for row in rows:
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break

                        anchor = row.select_one('a.iCIMS_Anchor')
                        if not anchor:
                            continue

                        title_h3 = anchor.find('h3')
                        title = title_h3.text.strip() if title_h3 else anchor.text.strip()
                        title = title.split('\n')[-1].strip()

                        job_url = anchor.get("href", "").strip()

                        if not self.should_process_job(title):
                            continue

                        desc_div = row.select_one('.description')
                        desc = desc_div.text.strip() if desc_div else "Vista Global career opportunities. Please visit the official career portal for more details."

                        location = "Unknown"
                        for dl in row.select('dl.iCIMS_JobHeaderGroup'):
                            text = dl.text.strip()
                            if "Job Location" in text:
                                lines = text.split('\n')
                                for idx, line in enumerate(lines):
                                    if "Job Location" in line and idx + 1 < len(lines):
                                        location = lines[idx+1].strip()
                                        break
                        
                        job_id = f"vistaglobal_{hash(job_url)}"

                        job = get_job_dict(
                            job_id=job_id,
                            title=title,
                            company=self.company_name,
                            location=location,
                            url=job_url,
                            source_url=url,
                            description=desc,
                            apply_url=job_url,
                            source=self.site_key
                        )

                        jobs.append(job)
                        added_on_page += 1

                    if added_on_page == 0 and len(rows) < 10:
                        break

                    page_num += 1

                return jobs

            except Exception as e:
                logger.error(f"[{self.site_key}] Error scraping: {e}")
                return jobs
            finally:
                await context.close()
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
