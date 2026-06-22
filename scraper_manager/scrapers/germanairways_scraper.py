import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class GermanAirwaysScraper(BaseScraper):
    """
    Scraper for German Airways (Personio)
    URL: https://german-airways.jobs.personio.de
    Platform: Personio
    """

    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="germanairways", db_manager=db_manager)
        self.base_url = "https://german-airways.jobs.personio.de"
        self.company_name = "German Airways"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Scrape jobs from German Airways Personio page
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
                        self.base_url, wait_until="domcontentloaded", timeout=60000
                    )
                    # Wait for job list
                    await page.wait_for_selector("a.job-box-link", timeout=20000)

                except Exception as e:
                    logger.error(f"[{self.site_key}] Navigation/Loading failed: {e}")
                    return []

                # Personio usually lists all jobs on one page for smaller companies
                # Check if we need to scroll or if it's all there.
                # Assuming single page for now based on analysis.

                job_items = await page.locator("a.job-box-link").all()
                logger.info(f"[{self.site_key}] Found {len(job_items)} jobs")

                for item in job_items:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    try:
                        # Title: First div inside the link
                        title_el = item.locator("div > div").first
                        if not await title_el.count():
                            continue
                        title = await title_el.text_content()
                        title = title.strip()

                        # Location: span > strong inside the second div usually
                        # Structure analysis:
                        # <div class="job-box-content"> -> Title
                        # <div class="job-box-content"> -> <span>Duration</span> <span><strong>Location</strong></span>
                        # Fix: Target specific container to avoid desktop/mobile duplicates
                        loc_el = item.locator(".multi-offices-desktop span > strong")
                        if not await loc_el.count():
                            # Fallback if class changes
                            loc_el = item.locator("span > strong").first

                        location = (
                            await loc_el.text_content()
                            if await loc_el.count()
                            else "Unknown Location"
                        )
                        location = location.strip()

                        # Link
                        link = await item.get_attribute("href")
                        if not link:
                            continue

                        # Ensure full URL
                        if not link.startswith("http"):
                            link = f"https://german-airways.jobs.personio.de{link}"

                        job = {
                            "company": self.company_name,
                            "title": title,
                            "location": location,
                            "url": link,
                            "source_url": link,
                            "apply_url": link,
                            "is_active": True,
                            "description": "",
                        }

                        jobs.append(job)

                    except Exception as e:
                        logger.warning(f"[{self.site_key}] Error parsing job item: {e}")
                        continue

                # Detail Extraction
                logger.info(
                    f"[{self.site_key}] Extracting details for {len(jobs)} jobs..."
                )
                for job in jobs:
                    if not job["url"]:
                        continue

                    if not self.should_process_job(job["title"]):
                        continue

                    try:
                        detail_page = await context.new_page()
                        await detail_page.goto(
                            job["url"], wait_until="domcontentloaded", timeout=30000
                        )

                        # Description
                        # Analysis: .job-detail-section or similar
                        # Personio usually has content in .job-detail-description or similar classes inside main
                        desc_el = detail_page.locator(".job-detail-section")
                        if await desc_el.count():
                            # If multiple sections, join them or take the container
                            job["description"] = (
                                await detail_page.locator(
                                    ".job-detail-content"
                                ).first.inner_html()
                                if await detail_page.locator(
                                    ".job-detail-content"
                                ).count()
                                else await desc_el.first.inner_html()
                            )
                        else:
                            # Fallback to main content
                            job["description"] = await detail_page.content()
                            # Backfill location from the original posting when missing.
                            if not job.get("location") or job.get("location") == "Unknown":
                                _loc = await self.extract_location_from_page(detail_page)
                                if _loc:
                                    job["location"] = _loc

                        # Apply Link - usually the same page has an Apply button that opens a form,
                        # but for scraper purposes the job URL is the apply start point.
                        # Sometimes there is a specific Apply button link.
                        apply_btn = detail_page.locator("a.apply-button")
                        if await apply_btn.count():
                            href = await apply_btn.first.get_attribute("href")
                            if href:
                                job["apply_url"] = (
                                    href
                                    if href.startswith("http")
                                    else f"https://german-airways.jobs.personio.de{href}"
                                )

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
