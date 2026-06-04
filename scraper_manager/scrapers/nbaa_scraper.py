import asyncio
import logging
import re
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class NBAAScraper(BaseScraper):
    """
    Scraper for NBAA (National Business Aviation Association)
    """

    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="nbaa", db_manager=db_manager)
        self.jobs_url = config.get("jobs_url", "https://jobs.nbaa.org/jobs/")
        self.base_url = config.get("base_url", "https://jobs.nbaa.org")
        self.company_name = "NBAA"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                # 1. Navigate to main listing
                logger.info(f"[{self.site_key}] Navigating to {self.jobs_url}")
                await page.goto(
                    self.jobs_url, wait_until="domcontentloaded", timeout=60000
                )
                await asyncio.sleep(5)

                while len(jobs) < (self.max_jobs or 50):
                    # 2. Extract job listing items
                    await page.wait_for_selector(
                        ".job-tile", state="attached", timeout=15000
                    )

                    # Extract structured data from the tiles
                    job_items = await page.evaluate("""() => {
                        const tiles = Array.from(document.querySelectorAll('.job-tile:not(#candidate-products-promotion)'));
                        return tiles.map(tile => {
                            const linkEl = tile.querySelector('a[title]');
                            const companyEl = tile.querySelector('.job-company-row');
                            const locationEl = tile.querySelector('.job-location');
                            const dateEl = tile.querySelector('.job-posted-date');
                            
                            return {
                                title: linkEl ? linkEl.innerText.trim() : null,
                                url: linkEl ? linkEl.getAttribute('href') : null,
                                company: companyEl ? companyEl.innerText.trim() : 'Unknown Company',
                                location: locationEl ? locationEl.innerText.trim() : 'Unknown',
                                posted_date_raw: dateEl ? dateEl.innerText.trim() : null
                            };
                        }).filter(item => item.title && item.url);
                    }""")

                    logger.info(
                        f"[{self.site_key}] Found {len(job_items)} potential jobs on current page"
                    )

                    # 3. Process each job
                    for item in job_items:
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break

                        title = item["title"]
                        url = item["url"]
                        if url.startswith("/"):
                            url = self.base_url.rstrip("/") + url

                        # Optimization: Filter by title BEFORE scraping detail page
                        if not self.should_process_job(title):
                            continue

                        if await self.is_url_already_scraped(url):
                            continue

                        logger.info(f"[{self.site_key}] Processing: {title}")

                        detail_page = None
                        try:
                            # Visit detailed page
                            detail_page = await context.new_page()
                            await detail_page.goto(
                                url, wait_until="domcontentloaded", timeout=30000
                            )
                            await self.random_delay(1, 2)

                            description = await self.extract_description_from_page(
                                detail_page
                            )

                            job_id = f"{self.site_key}_{re.sub(r'[^a-zA-Z0-9]', '', url)[-15:]}"

                            job_data = get_job_dict(
                                job_id=job_id,
                                title=title,
                                company=item["company"],
                                location=item["location"],
                                description=description,
                                url=url,
                                source_url=self.jobs_url,
                                source=self.site_key,
                                posted_date=self.parse_posted_date(
                                    item["posted_date_raw"]
                                )
                                if item["posted_date_raw"]
                                else None,
                            )

                            jobs.append(job_data)

                        except Exception as e:
                            logger.error(
                                f"[{self.site_key}] Error on detail page {url}: {e}"
                            )
                        finally:
                            if detail_page:
                                await detail_page.close()

                    # 4. Pagination
                    if (self.max_jobs and len(jobs) >= self.max_jobs) or len(
                        job_items
                    ) == 0:
                        break

                    next_el = await page.query_selector(
                        'a[aria-label="Next Page"], a[rel="next"], li.next a'
                    )
                    if next_el:
                        logger.info(f"[{self.site_key}] Moving to next page...")
                        await next_el.click()
                        await asyncio.sleep(5)
                    else:
                        break

            except Exception as e:
                logger.error(f"[{self.site_key}] Main execution error: {e}")
            finally:
                await context.close()
                await browser.close()

        return jobs

    async def run(self):
        """Main entry point"""
        self.print_header()
        jobs = await self.fetch_jobs()

        # Standard cleaning
        jobs = [j for j in jobs if j is not None]

        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
