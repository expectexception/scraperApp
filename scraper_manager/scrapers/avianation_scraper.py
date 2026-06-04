import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class AvianationScraper(BaseScraper):
    """
    Scraper for Avianation.com
    Navigates main listing -> Detail pages
    """

    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="avianation", db_manager=db_manager)
        self.jobs_url = config.get("jobs_url", "https://www.avianation.com/")
        self.base_url = config.get("base_url", "https://www.avianation.com")

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

                # 2. Extract job links from main page
                # Wait for potential content load
                await asyncio.sleep(3)

                # Get all unique job links
                # Search for links that look like job details
                # The chunk showed links to /jobs/...
                job_links_set = set()
                elements = await page.query_selector_all('a[href*="/jobs/"]')

                for el in elements:
                    href = await el.get_attribute("href")
                    if href and "/jobs/" in href:
                        # Ensure full URL
                        full_url = (
                            self.base_url.rstrip("/") + href
                            if href.startswith("/")
                            else href
                        )
                        if "www.avianation.com" not in full_url:
                            if href.startswith("/"):
                                full_url = self.base_url.rstrip("/") + href
                            else:
                                # handle relative paths not starting with / if any
                                pass
                        job_links_set.add(full_url)

                logger.info(
                    f"[{self.site_key}] Found {len(job_links_set)} potential jobs"
                )

                # 3. Visit each job
                for url in list(job_links_set)[: self.max_jobs]:
                    if len(jobs) >= self.max_jobs:
                        break

                    if await self.is_url_already_scraped(url):
                        continue

                    try:
                        detail_page = await context.new_page()
                        await detail_page.goto(
                            url, wait_until="domcontentloaded", timeout=30000
                        )

                        # Extract Details
                        title_el = await detail_page.query_selector("h1")
                        title = (
                            await title_el.inner_text() if title_el else "Unknown Title"
                        )

                        logger.info(f"[{self.site_key}] Processing: {title}")

                        # Description
                        description = await self.extract_description_from_page(
                            detail_page
                        )

                        # Metadata
                        # Common pattern on avianation detail pages:
                        # Header area might contain company, location etc.
                        # H2 usually is company?
                        # Let's try to grab all text and regex or use specific selectors if standard

                        await detail_page.inner_text("body")

                        location = "Unknown"
                        # Regex for Location: ...
                        # Or look for schema.org data if available?

                        # Try finding company name - often h2 or below h1
                        company = "AviaNation"  # Fallback
                        h2_el = await detail_page.query_selector("h2")
                        if h2_el:
                            company = await h2_el.inner_text()

                        # Try to find specific "Apply" button
                        apply_btn = await detail_page.query_selector(
                            'a:has-text("Apply"), a[class*="apply"]'
                        )
                        apply_url = url
                        if apply_btn:
                            href = await apply_btn.get_attribute("href")
                            if href and href.startswith("http"):
                                apply_url = href

                        job_data = {
                            "company": company.strip(),
                            "title": title.strip(),
                            "location": location,
                            "description": description,
                            "source_url": url,
                            "apply_url": apply_url,
                            "url": url,
                            "posted_date": datetime.now().isoformat(),
                            "is_active": True,
                        }

                        jobs.append(job_data)
                        await detail_page.close()

                    except Exception as e:
                        logger.error(f"[{self.site_key}] Error processing {url}: {e}")

            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")

        return jobs

    async def run(self):
        """Main entry point"""
        self.print_header()
        jobs = await self.fetch_jobs()

        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
