import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class UnitedScraper(BaseScraper):
    """
    Scraper for United Airlines Careers
    URL: https://careers.united.com/us/en/search-results
    Platform: Phenom People
    """

    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="united", db_manager=db_manager)
        self.base_url = config.get("sites", {}).get("united", {}).get("base_url", "https://careers.united.com")
        self.jobs_url = config.get("sites", {}).get("united", {}).get("jobs_url", "https://careers.united.com/us/en/operations-search-results-page")
        self.company_name = "United Airlines"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Scrape jobs from United careers page (Listing only)
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
                        self.jobs_url, wait_until="domcontentloaded", timeout=60000
                    )
                    await page.wait_for_timeout(5000)

                    # Close cookie consent if it exists
                    try:
                        cookie_btn = page.locator(
                            "#gdpr-cookie-accept, .cookie-accept-btn"
                        )
                        if await cookie_btn.count():
                            await cookie_btn.first.click()
                    except:
                        pass

                    # Close bot/chat if it exists
                    try:
                        await page.locator(".phenom-bot-close").click(timeout=2000)
                    except:
                        pass

                    # Wait for job list
                    await page.wait_for_selector("li.jobs-list-item", timeout=20000)
                except Exception as e:
                    logger.error(f"[{self.site_key}] Navigation/Loading failed: {e}")
                    # Capture screenshot for debugging if it fails
                    await page.screenshot(path=f"{self.site_key}_error.png")
                    return []

                while True:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    job_items = await page.locator("li.jobs-list-item").all()
                    logger.info(
                        f"[{self.site_key}] Found {len(job_items)} jobs on current page"
                    )

                    for item in job_items:
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break
                        try:
                            # Phenom People specific selectors
                            title_el = item.locator('[data-ph-at-id="job-title-text"]')
                            if not await title_el.count():
                                title_el = item.locator(".job-title")

                            if not await title_el.count():
                                continue

                            title = (await title_el.text_content()).strip()

                            loc_el = item.locator(
                                '[data-ph-at-id="job-location-text"]'
                            ) or item.locator(".job-location")
                            location = (
                                (
                                    await loc_el.text_content()
                                    if await loc_el.count()
                                    else "United States"
                                )
                                .strip()
                                .replace("\n", " ")
                            )

                            link_el = item.locator('a[data-ph-at-id="job-link"]')
                            if not await link_el.count():
                                link_el = item.locator("a.au-target").first

                            link = await link_el.get_attribute("href")
                            if not link:
                                continue

                            if not link.startswith("http"):
                                link = (
                                    f"https://careers.united.com{link}"
                                    if link.startswith("/")
                                    else f"https://careers.united.com/us/en/{link}"
                                )

                            jobs.append(
                                {
                                    "company": self.company_name,
                                    "title": title,
                                    "location": location,
                                    "url": link,
                                    "source_url": link,
                                    "apply_url": link,
                                    "is_active": True,
                                }
                            )
                        except Exception as e:
                            logger.debug(
                                f"[{self.site_key}] Error parsing job item: {e}"
                            )
                            continue

                    # Pagination
                    next_btn = page.locator('a[data-ph-at-id="pagination-next"]')
                    if await next_btn.is_visible() and await next_btn.is_enabled():
                        classes = await next_btn.get_attribute("class") or ""
                        if "disabled" in classes.lower():
                            break

                        await next_btn.click()
                        await page.wait_for_timeout(3000)
                        await page.wait_for_selector("li.jobs-list-item", timeout=10000)
                    else:
                        break
            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
            finally:
                await browser.close()

        return jobs

    async def fetch_job_descriptions(
        self, jobs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Fetch full details for matched jobs only"""
        if not jobs:
            return []

        logger.info(
            f"[{self.site_key}] Fetching descriptions for {len(jobs)} matched jobs..."
        )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context()

            for job in jobs:
                page = await context.new_page()
                try:
                    await page.goto(
                        job["url"], wait_until="domcontentloaded", timeout=30000
                    )
                    # Descriptions are usually in .job-description or .content
                    desc_el = page.locator(
                        ".job-description, .job-details-brief, .content"
                    )
                    job["description"] = (
                        await desc_el.first.inner_html()
                        if await desc_el.count()
                        else await page.content()
                    )

                    # Look for explicit Apply button
                    apply_btn = page.locator(
                        'a.primary-button, a[data-ph-at-id="apply-link"]'
                    )
                    if await apply_btn.count():
                        href = await apply_btn.first.get_attribute("href")
                        if href:
                            job["apply_url"] = (
                                href
                                if href.startswith("http")
                                else f"https://careers.united.com{href}"
                            )
                except Exception as e:
                    logger.warning(
                        f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}"
                    )
                finally:
                    await page.close()
                await asyncio.sleep(0.5)

            await browser.close()
        return jobs

    async def run(self):
        """Main execution method"""
        self.print_header()

        # 1. Discovery
        jobs = await self.fetch_jobs()
        if not jobs:
            return []

        # 2. Pre-filter
        if self.use_filter and self.filter_manager:
            logger.info(f"[{self.site_key}] Applying pre-filter...")
            matched_jobs, rejected_jobs, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)
            if not matched_jobs:
                return []
            jobs = matched_jobs

        # 3. Duplicates
        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []

        # 4. Enrichment
        jobs = await self.fetch_job_descriptions(jobs)

        # 5. Save
        await self.save_results(jobs)
        return jobs
