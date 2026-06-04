import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class LufthansaScraper(BaseScraper):
    """
    Scraper for Lufthansa Group Careers
    URL: https://apply.lufthansagroup.careers/index.php?ac=search_result&search_criterion_channel%5B%5D=12&language=2
    """

    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="lufthansa", db_manager=db_manager)
        self.base_url = "https://apply.lufthansagroup.careers/index.php?ac=search_result&search_criterion_channel%5B%5D=12&language=2"
        self.company_name = "Lufthansa Group"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Scrape jobs from Lufthansa careers page
        """
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )

            try:
                page = await context.new_page()
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")

                try:
                    # Relaxed wait condition to domcontentloaded as networkidle can flake on complex sites
                    await page.goto(
                        self.base_url, wait_until="domcontentloaded", timeout=60000
                    )

                    # Wait a bit for initial dynamic content
                    await page.wait_for_timeout(5000)

                    # Removed cookie click logic

                    # Wait for job cards to appear explicitly
                    try:
                        await page.wait_for_selector(
                            ".jobboard-datatable a", timeout=30000
                        )
                    except Exception:
                        logger.warning(
                            f"[{self.site_key}] Job cards not found after waiting."
                        )
                except Exception as e:
                    logger.error(f"[{self.site_key}] Navigation failed: {e}")
                    return []

                # Infinite Scroll Logic
                last_height = await page.evaluate("document.body.scrollHeight")
                job_count_prev = 0
                retries = 0

                while True:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    # Get all job cards
                    job_cards = await page.locator(
                        '.jobboard-datatable a[href*="index.php?ac=jobad"]'
                    ).all()

                    if len(job_cards) == job_count_prev:
                        retries += 1
                        if retries > 3:  # No new jobs after 3 scrolls
                            logger.info(
                                f"[{self.site_key}] Reached end of list or no new jobs loading."
                            )
                            break
                    else:
                        retries = 0  # Reset retries if we found new jobs

                    job_count_prev = len(job_cards)
                    logger.info(f"[{self.site_key}] Visible jobs: {job_count_prev}")

                    # Scroll to bottom
                    await page.evaluate(
                        "window.scrollTo(0, document.body.scrollHeight)"
                    )

                    # Wait for load
                    try:
                        await page.wait_for_timeout(
                            2000
                        )  # Fixed wait for animation/fetch
                        new_height = await page.evaluate("document.body.scrollHeight")
                        if new_height == last_height and retries > 2:
                            # Try to check if there is a 'load more' button just in case
                            pass
                        last_height = new_height
                    except Exception:
                        pass

                    # Safety break for massive lists if we just want to test or limit
                    if self.max_jobs and job_count_prev >= self.max_jobs:
                        break

                    # Cap at reasonable scroll depth if unlimited to avoid infinite loops
                    if job_count_prev > 500:
                        logger.info(
                            f"[{self.site_key}] Reached safety limit of 500 jobs."
                        )
                        break

                # Extract jobs from collected cards
                # Note: Playwright elements can become stale if we scrape after scrolling.
                # Safer to extract metadata from all accumulated cards OR iterate and extract

                logger.info(
                    f"[{self.site_key}] Extracting data from {len(job_cards)} job cards..."
                )

                initial_jobs = []
                for i, card in enumerate(job_cards):
                    if self.max_jobs and len(initial_jobs) >= self.max_jobs:
                        break

                    try:
                        title_el = card.locator("h2")
                        if not await title_el.count():
                            continue

                        title = await title_el.text_content()
                        title = title.strip() if title else "Unknown Title"

                        company_el = card.locator(".company-name")
                        company = (
                            await company_el.text_content()
                            if await company_el.count()
                            else self.company_name
                        )
                        company = company.strip()

                        location_el = (
                            card.locator(".jobad-meta-item")
                            .first.locator("span")
                            .nth(1)
                        )
                        location = (
                            await location_el.text_content()
                            if await location_el.count()
                            else "Unknown Location"
                        )
                        location = location.strip()

                        link = await card.get_attribute("href")
                        if not link:
                            continue
                        if not link.startswith("http"):
                            link = (
                                f"https://apply.lufthansagroup.careers/{link}"
                                if link.startswith("/")
                                else f"https://apply.lufthansagroup.careers/index.php{link}"
                            )

                        initial_jobs.append(
                            {
                                "company": company,
                                "title": title,
                                "location": location,
                                "url": link,
                                "source_url": link,
                                "apply_url": link,
                                "is_active": True,
                                "description": "",
                            }
                        )
                    except Exception as e:
                        logger.warning(
                            f"[{self.site_key}] Error extracting job card {i}: {e}"
                        )

                # PRE-FILTER: Filter by title first to skip irrelevant roles COMPLETELY
                logger.info(
                    f"[{self.site_key}] {len(initial_jobs)} potential jobs. Applying pre-filter..."
                )
                matched_initial, _, _ = self.apply_title_filter(initial_jobs)
                logger.info(
                    f"[{self.site_key}] {len(matched_initial)} jobs passed pre-filtering. Fetching details..."
                )

                # Now fetch descriptions only for MATCHED jobs
                for job in matched_initial:
                    try:
                        if not self.should_process_job(job["title"]):
                            continue

                        if await self.is_url_already_scraped(job["url"]):
                            continue

                        logger.info(
                            f"[{self.site_key}] Fetching details for: {job['title']}"
                        )
                        detail_page = await context.new_page()
                        # Increased timeout for stability
                        await detail_page.goto(
                            job["url"], wait_until="load", timeout=60000
                        )

                        description_el = detail_page.locator("div.jobad-content")
                        if not await description_el.count():
                            description = await detail_page.content()
                        else:
                            description = await description_el.first.inner_html()

                        job["description"] = description

                        apply_btn = detail_page.locator(".js-button-apply")
                        if await apply_btn.count():
                            apply_href = await apply_btn.get_attribute("href")
                            if apply_href:
                                job["apply_url"] = (
                                    apply_href
                                    if apply_href.startswith("http")
                                    else f"https://apply.lufthansagroup.careers/{apply_href}"
                                )

                        jobs.append(
                            job
                        )  # ADDED THIS LINE: Actually add to final results
                        await detail_page.close()
                        await asyncio.sleep(0.5)

                    except Exception as e:
                        logger.warning(
                            f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}"
                        )

            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
            finally:
                await browser.close()

        return jobs

    async def run(self):
        """Main entry point for the scraper"""
        self.print_header()
        jobs = await self.fetch_jobs()
        # Filter out any None values
        jobs = [j for j in jobs if j is not None]
        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
