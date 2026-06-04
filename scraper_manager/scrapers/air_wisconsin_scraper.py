import asyncio
import logging
from typing import List, Dict
from .base_scraper import BaseScraper
from .job_schema import get_job_dict
from playwright.async_api import async_playwright
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class AirWisconsinScraper(BaseScraper):
    """Scraper for Air Wisconsin using their UKG Pro (Ultipro) portal via Playwright."""

    def __init__(self, config: Dict, db_manager=None):
        super().__init__(config, site_key="air_wisconsin", db_manager=db_manager)
        self.base_url = "https://recruiting2.ultipro.com/AIR1002AIRWI/JobBoard/74c69cd1-e0aa-4364-8c31-c93dc910998d/"

    async def fetch_jobs(self) -> List[Dict]:
        """Fetch jobs from the UKG Pro portal using Playwright."""
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                # Add a query parameter to sort by date desc if possible (based on user URL)
                target_url = self.base_url + "?q=&o=postedDateDesc"
                logger.info(f"[{self.site_key}] Navigating to {target_url}...")
                await page.goto(target_url, wait_until="networkidle", timeout=60000)

                # Wait for job container to appear
                try:
                    await page.wait_for_selector(
                        '[data-automation="opportunity"], .opportunity', timeout=30000
                    )
                except Exception as e:
                    logger.warning(
                        f"[{self.site_key}] Timeout waiting for job list: {e}"
                    )

                # Handle "Load More" if it exists
                load_more_attempts = 0
                max_load_more = 5
                while load_more_attempts < max_load_more:
                    load_more_btn = await page.query_selector(
                        'button:has-text("Load More"), [data-automation="load-more"]'
                    )
                    if load_more_btn and await load_more_btn.is_visible():
                        logger.info(
                            f"[{self.site_key}] Clicking 'Load More' (Attempt {load_more_attempts + 1})..."
                        )
                        await load_more_btn.click()
                        await asyncio.sleep(2)
                        load_more_attempts += 1
                    else:
                        break

                # Extract job summary data from the list
                job_elements = await page.query_selector_all(
                    '[data-automation="opportunity"]'
                )
                if not job_elements:
                    job_elements = await page.query_selector_all(".opportunity")

                logger.info(
                    f"[{self.site_key}] Found {len(job_elements)} job elements on the board."
                )

                job_data_list = []
                for el in job_elements:
                    title_el = await el.query_selector(
                        '[data-automation="job-title"], h3 a'
                    )
                    if not title_el:
                        continue

                    title = (await title_el.inner_text()).strip()
                    href = await title_el.get_attribute("href")
                    if not href:
                        continue

                    job_url = urljoin(self.base_url, href)

                    # Get location
                    location = "Unknown"
                    loc_el = await el.query_selector(
                        '[data-automation="job-location"], .opportunity-location'
                    )
                    if not loc_el:
                        loc_el = await el.query_selector(
                            '[data-automation="job-address"]'
                        )

                    if loc_el:
                        location_text = (await loc_el.inner_text()).strip()
                        if location_text:
                            location = self.normalize_location(location_text)

                    # Early filtering by title
                    if not self.should_process_job(title):
                        continue

                    # Duplicate check
                    if await self.is_url_already_scraped(job_url):
                        continue

                    job_data_list.append(
                        {"title": title, "url": job_url, "location": location}
                    )

                    if self.max_jobs and len(job_data_list) >= self.max_jobs:
                        break

                # Now fetch details for each matched job
                for item in job_data_list:
                    logger.info(
                        f"[{self.site_key}] Fetching details for: {item['title']}..."
                    )
                    await page.goto(
                        item["url"], wait_until="domcontentloaded", timeout=60000
                    )

                    # Wait for description
                    try:
                        await page.wait_for_selector(
                            '[data-automation="job-description"], .opportunity-description',
                            timeout=15000,
                        )
                        desc_el = await page.query_selector(
                            '[data-automation="job-description"], .opportunity-description'
                        )
                        description = (
                            await desc_el.inner_html()
                            if desc_el
                            else "Description not found."
                        )
                    except:
                        description = "Description timeout or not found."

                    job = get_job_dict(
                        job_id=f"{self.site_key}_{hash(item["url"])}",
                        title=item["title"],
                        company=self.company_name,
                        location=item["location"],
                        url=item["url"],
                        source_url=self.base_url if hasattr(self, 'base_url') else item["url"],
                        description=description,
                        apply_url=item["url"],
                        source=self.site_key
                    )
                    jobs.append(job)

                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                return jobs

            except Exception as e:
                logger.error(f"[{self.site_key}] Scraper failed: {e}")
                return jobs
            finally:
                await browser.close()

    async def run(self):
        """Standard execution method."""
        self.print_header()

        jobs = await self.fetch_jobs()

        # Final match filtering
        matched_jobs, rejected_jobs, stats = self.apply_title_filter(jobs)

        # Save to DB
        await self.save_results(matched_jobs)

        return matched_jobs
