import logging
import asyncio
from typing import List, Dict
from urllib.parse import urljoin
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class GlobeairScraper(BaseScraper):
    """
    Scraper for GlobeAir using Playwright.
    URL: https://www.globeair.com/career#openpositions
    """

    def __init__(self, config: Dict, db_manager=None):
        super().__init__(config, site_key="globeair", db_manager=db_manager)
        self.base_url = "https://www.globeair.com/career"
        self.company_name = "GlobeAir"

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
                await page.wait_for_timeout(5000)
                
                # Scroll a bit to trigger lazy loading
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(3000)

                # Look for open positions container.
                # NOTE: GlobeAir's "View opportunity" links use a short "/j/<id>" URL
                # pattern (not "job"/"position" in the href), and the actual job title
                # lives in a sibling <strong> tag rather than the link text itself.
                job_elements = await page.query_selector_all(
                    'a[href*="job"], a[href*="position"], a[href*="/j/"]'
                )

                logger.info(f"[{self.site_key}] Found {len(job_elements)} potential job links.")

                for el in job_elements:
                    href = await el.get_attribute("href")
                    if not href or "faq" in href.lower():
                        continue
                    if (
                        "/j/" not in href.lower()
                        and "career" not in href.lower()
                        and "job" not in href.lower()
                    ):
                        continue

                    title = await el.evaluate(
                        """el => {
                            const strong = el.parentElement?.querySelector('strong');
                            if (strong && strong.textContent.trim()) return strong.textContent.trim();
                            const prev = el.parentElement?.previousElementSibling;
                            if (prev && prev.textContent.trim()) return prev.textContent.trim();
                            return el.textContent.trim();
                        }"""
                    )
                    title = (title or "").strip()

                    if not title or len(title) < 3:
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
                        description="GlobeAir Career Opportunity.",
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
