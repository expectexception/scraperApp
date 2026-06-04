import logging
from typing import List, Dict
from .base_scraper import BaseScraper
from .job_schema import get_job_dict
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class OmniAirScraper(BaseScraper):
    """Scraper for Omni Air International using their ADP Workforce Now portal via Playwright."""

    def __init__(self, config: Dict, db_manager=None):
        super().__init__(config, site_key="omni_air", db_manager=db_manager)
        self.base_url = "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid=a7828c0b-d30d-40a2-a3ee-61c80628985c&ccId=19000101_000001&lang=en_US&selectedMenuKey=CurrentOpenings"

    async def fetch_jobs(self) -> List[Dict]:
        """Fetch jobs from the ADP Workforce Now portal using Playwright."""
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()

            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until="networkidle", timeout=60000)

                # Wait for the job list to load
                try:
                    await page.wait_for_selector(
                        ".current-openings-item", timeout=30000
                    )
                except Exception as e:
                    logger.warning(
                        f"[{self.site_key}] Timeout waiting for job list: {e}"
                    )
                    return jobs

                # ADP is an SPA. We'll extract titles and locations first, then click each to get descriptions.
                # However, to avoid state issues, we'll click, scrape, go back, and repeat.

                # Note: ADP often uses dynamic IDs. We'll use the title selectors.

                # Find all job items
                job_items = await page.query_selector_all(".current-openings-item")
                logger.info(
                    f"[{self.site_key}] Found {len(job_items)} job items on the initial page."
                )

                for i in range(len(job_items)):
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    # Re-find items because DOM might change after going back
                    current_items = await page.query_selector_all(
                        ".current-openings-item"
                    )
                    if i >= len(current_items):
                        break

                    item = current_items[i]
                    title_el = await item.query_selector(".current-opening-title")
                    if not title_el:
                        continue

                    title = (await title_el.inner_text()).strip()

                    loc_el = await item.query_selector(".current-opening-location-item")
                    location = (
                        (await loc_el.inner_text()).strip() if loc_el else "Unknown"
                    )

                    # Since there are no direct URLs in the list for ADP, we'll generate a consistent one
                    # based on the CID and the job title/location to track duplicates.
                    # A better way is to find an internal ID if possible.
                    job_pseudo_url = f"{self.base_url}#{title.replace(' ', '_')}_{location.replace(' ', '_')}"

                    # Early filtering by title
                    if not self.should_process_job(title):
                        continue

                    # Duplicate check
                    if await self.is_url_already_scraped(job_pseudo_url):
                        continue

                    logger.info(f"[{self.site_key}] Clicking into: {title}...")

                    # Click to open details
                    await title_el.click()

                    # Wait for description to load
                    try:
                        await page.wait_for_selector(
                            ".job-description-details", timeout=15000
                        )
                        desc_el = await page.query_selector(".job-description-details")
                        description = (
                            await desc_el.inner_html()
                            if desc_el
                            else "Description not found."
                        )

                        job = get_job_dict(
                            job_id=f"{self.site_key}_{hash(job_pseudo_url)}",
                            title=title,
                            company=self.company_name,
                            location=location,
                            url=job_pseudo_url,
                            source_url=self.base_url if hasattr(self, 'base_url') else job_pseudo_url,
                            description=description,
                            apply_url=job_pseudo_url,
                            source=self.site_key
                        )
                        jobs.append(job)

                    except Exception as e:
                        logger.warning(
                            f"[{self.site_key}] Failed to load details for {title}: {e}"
                        )

                    # Go back to list
                    back_btn = await page.query_selector(
                        "#recruitment_jobDescription_back"
                    )
                    if back_btn:
                        await back_btn.click()
                        await page.wait_for_selector(
                            ".current-openings-item", timeout=10000
                        )
                    else:
                        logger.warning(
                            f"[{self.site_key}] Back button not found, attempting reload..."
                        )
                        await page.goto(self.base_url, wait_until="networkidle")

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
