import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class StarAirScraper(BaseScraper):
    """
    Scraper for Star Air Careers
    URL: https://www.starair.in/careers
    """

    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="starair", db_manager=db_manager)
        self.base_url = "https://www.starair.in/careers"
        self.domain = "https://www.starair.in"
        self.company_name = "Star Air"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Scrape jobs from Star Air careers page
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
                    await page.goto(
                        self.base_url, wait_until="networkidle", timeout=60000
                    )
                except Exception as e:
                    logger.error(f"[{self.site_key}] Navigation failed: {e}")
                    return []

                # Check for table
                table = page.locator("table.table-bordered")
                if not await table.is_visible():
                    logger.warning(f"[{self.site_key}] Job table not found")
                    return []

                # Get all rows (skipping header)
                rows = await table.locator("tr").all()
                # Skip the first row (header) if it exists
                if rows:
                    rows = rows[1:]

                logger.info(f"[{self.site_key}] Found {len(rows)} potential job rows")

                for i, row in enumerate(rows):
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    try:
                        # Extract basic info from the row
                        title_link = row.locator("td:nth-child(2) a")
                        location_cell = row.locator("td:nth-child(4)")

                        if not await title_link.count():
                            continue

                        title = await title_link.text_content()
                        title = title.strip() if title else "Unknown Title"

                        relative_link = await title_link.get_attribute("href")
                        full_link = (
                            f"{self.domain}{relative_link}"
                            if relative_link
                            else self.base_url
                        )

                        location = await location_cell.text_content()
                        location = location.strip() if location else "Unknown Location"

                        # Apply URL is usually on the details page, but we can infer or fetch it
                        # For now, let's use the details page as the apply URL or source URL

                        job = {
                            "company": self.company_name,
                            "title": title,
                            "location": location,
                            "url": full_link,
                            "source_url": full_link,
                            "apply_url": full_link,  # Will try to find better one in details
                            "is_active": True,
                            "description": "",
                        }

                        # Go to details page to get description
                        try:
                            if not self.should_process_job(title):
                                continue

                            if await self.is_url_already_scraped(full_link):
                                continue

                            logger.info(
                                f"[{self.site_key}] Fetching details for: {title}"
                            )
                            detail_page = await context.new_page()
                            await detail_page.goto(
                                full_link, wait_until="domcontentloaded", timeout=30000
                            )

                            # Get description - usually in a specific container
                            # Based on standard bootstrap sites, it might be in a 'container' or specific div
                            # Let's try to grab the main content
                            description = ""

                            # Try common content areas
                            content_locators = [
                                ".col-md-12",  # Generic
                                ".panel-body",
                                "form",  # Sometimes job details are inside a form view
                            ]

                            for loc in content_locators:
                                if await detail_page.locator(loc).first.is_visible():
                                    description = await detail_page.locator(
                                        loc
                                    ).first.inner_html()
                                    break

                            if not description:
                                description = (
                                    await detail_page.content()
                                )  # Fallback to full content if specific area not found

                            job["description"] = description

                            # Check for Apply button URL
                            apply_btn = detail_page.locator(
                                "text=Apply"
                            )  # Simple text match
                            if await apply_btn.count() > 0:
                                # Sometimes it's a link, sometimes a button
                                # If it navigates to a new page, that's the apply url.
                                # But getting the href is safer if it is an anchor
                                apply_href = await apply_btn.get_attribute("href")
                                if apply_href:
                                    job["apply_url"] = (
                                        f"{self.domain}{apply_href}"
                                        if apply_href.startswith("/")
                                        else apply_href
                                    )

                            await detail_page.close()

                        except Exception as e:
                            logger.warning(
                                f"[{self.site_key}] Failed to fetch details for {title}: {e}"
                            )
                            # Keep the job even if details fail, just without description

                        jobs.append(job)

                    except Exception as e:
                        logger.error(f"[{self.site_key}] Error parsing row {i}: {e}")
                        continue

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
