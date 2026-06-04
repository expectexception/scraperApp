import asyncio
import logging
import re
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class CPRScraper(BaseScraper):
    """
    Scraper for Canadian Pacific Kansas City (CPKC)
    """

    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="cpr", db_manager=db_manager)
        self.jobs_url = config.get(
            "jobs_url",
            "https://careers.cpr.ca/search/?q=&locationsearch=&skillsSearch=false&sortBy=date&pageNumber=0",
        )
        self.company_name = "CPKC"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                # 1. Navigate to main listing
                logger.info(f"[{self.site_key}] Navigating to {self.jobs_url}")
                await page.goto(
                    self.jobs_url, wait_until="domcontentloaded", timeout=90000
                )
                await asyncio.sleep(5)  # Allow dynamic loading

                while len(jobs) < (self.max_jobs or 50):
                    # 2. Extract job listing items
                    # SuccessFactors typically has a table with job links and titles
                    await page.wait_for_selector(
                        'a.jobTitle-link, a[href*="/job/"]',
                        state="attached",
                        timeout=15000,
                    )

                    # Extract title and URL pairs from the listing page
                    extracted_links = await page.evaluate("""() => {
                        return Array.from(document.querySelectorAll('a[href*="/job/"]'))
                            .map(a => {
                                const title = a.innerText.trim();
                                const href = a.getAttribute('href');
                                return { title, href };
                            })
                            .filter(item => item.title && item.href);
                    }""")

                    seen_urls_in_batch = set()
                    job_items = []
                    for item in extracted_links:
                        full_url = item["href"]
                        if full_url.startswith("/"):
                            full_url = "https://careers.cpr.ca" + full_url

                        if full_url not in seen_urls_in_batch:
                            seen_urls_in_batch.add(full_url)
                            job_items.append({"title": item["title"], "url": full_url})

                    logger.info(
                        f"[{self.site_key}] Found {len(job_items)} potential jobs on current page"
                    )

                    # 3. Process each job
                    for item in job_items:
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break

                        title = item["title"]
                        url = item["url"]

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

                            # Location extraction
                            location = "Canada"
                            loc_el = await detail_page.query_selector(
                                ".jobGeoLocation, .location, span.custom_location"
                            )
                            if loc_el:
                                location = (await loc_el.inner_text()).strip()
                            else:
                                # Fixed the missing selector error: Page.inner_text('body')
                                body_text = await detail_page.inner_text("body")
                                loc_match = re.search(
                                    r"Location:\s*([^\n,]+)", body_text
                                )
                                if loc_match:
                                    location = loc_match.group(1).strip()

                            # Extract posted date if possible
                            posted_date = await self.extract_posted_date_from_page(
                                detail_page
                            )

                            job_id = f"{self.site_key}_{re.sub(r'[^a-zA-Z0-9]', '', url)[-15:]}"

                            job_data = get_job_dict(
                                job_id=job_id,
                                title=title,
                                company=self.company_name,
                                location=location,
                                description=description,
                                url=url,
                                source_url=self.jobs_url,
                                source=self.site_key,
                                posted_date=posted_date,
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
                        'a[title="Next Page"], .pagination-next a, a:has-text("»")'
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
