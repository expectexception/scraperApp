import logging
import re
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class AtlanticAviationScraper(BaseScraper):
    """
    Scraper for Atlantic Aviation (Talentcare/WordPress)
    URL: https://atlanticaviationcareers.com/
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="atlantic_aviation", db_manager=db_manager)
        self.base_url = "https://atlanticaviationcareers.com/"
        self.company_name = "Atlantic Aviation"

    async def fetch_jobs(self) -> list:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(
                    self.base_url, wait_until="domcontentloaded", timeout=60000
                )

                # Navigate to the jobs section if needed
                # According to exploration, jobs are on the home page or reached via scroll/click
                await page.wait_for_timeout(3000)

                # Scroll to ensure FacetWP loads
                await self.auto_scroll(page)

                page_count = 1
                while True:
                    if self.max_pages and page_count > self.max_pages:
                        break

                    logger.info(f"[{self.site_key}] Processing page {page_count}...")

                    # Wait for job row selector
                    try:
                        await page.wait_for_selector(
                            "div.jl-entry-categories", timeout=15000
                        )
                    except:
                        logger.warning(
                            f"[{self.site_key}] No jobs found or selector timeout on page {page_count}"
                        )
                        break

                    job_rows = await page.query_selector_all("div.jl-entry-categories")
                    if not job_rows:
                        break

                    logger.info(
                        f"[{self.site_key}] Found {len(job_rows)} job rows on page {page_count}"
                    )

                    page_jobs_data = []
                    for row in job_rows:
                        try:
                            # Title and Link are in a.joblinks
                            link_el = await row.query_selector("a.joblinks")
                            if not link_el:
                                continue

                            full_text = await link_el.inner_text()
                            url = await link_el.get_attribute("href")

                            # Clean title and extract location
                            # Format usually: "Job Title - Location" or contains a span.loc-stuff
                            loc_el = await link_el.query_selector("span.loc-stuff")
                            location = "USA"
                            if loc_el:
                                location = await loc_el.inner_text()
                                # Title is usually the text before the dash or exclusion of span
                                # We can get the title by removing the location text
                                title = (
                                    full_text.replace(location, "")
                                    .strip()
                                    .strip("-")
                                    .strip()
                                )
                            else:
                                title = full_text.strip()

                            # Extract ID from URL: .../location-name-12345/
                            match = re.search(r"-(\d+)/?$", url)
                            job_id = match.group(1) if match else str(hash(url))

                            page_jobs_data.append(
                                {
                                    "title": title,
                                    "url": url,
                                    "location": location,
                                    "job_id": job_id,
                                }
                            )
                        except Exception as e:
                            logger.error(f"[{self.site_key}] Error parsing row: {e}")
                            continue

                    # Process jobs on this page
                    for job_data in page_jobs_data:
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break

                        if not self.should_process_job(job_data["title"]):
                            continue

                        if await self.is_url_already_scraped(job_data["url"]):
                            continue

                        try:
                            logger.info(
                                f"[{self.site_key}] Fetching details for: {job_data['url']}"
                            )
                            detail_page = await context.new_page()
                            await detail_page.goto(
                                job_data["url"],
                                wait_until="domcontentloaded",
                                timeout=30000,
                            )
                            await detail_page.wait_for_timeout(2000)

                            # Description cleaning logic
                            # WordPress sites usually have content in .entry-content or .job-description
                            desc_el = await detail_page.query_selector(
                                ".entry-content, .job-description, .tc-job-listing-description"
                            )
                            description = ""
                            if desc_el:
                                description = await desc_el.inner_text()
                            else:
                                description = await self.extract_description_from_page(
                                    detail_page
                                )

                            job = get_job_dict(
                                job_id=f"atlantic_{job_data['job_id']}",
                                title=job_data["title"],
                                company=self.company_name,
                                location=job_data["location"],
                                url=job_data["url"],
                                source_url=self.base_url,
                                description=description.strip(),
                                apply_url=job_data["url"],
                                posted_date=None,
                                source=self.site_key,
                            )

                            jobs.append(job)
                            await detail_page.close()
                            await self.random_delay(1, 3)

                        except Exception as e:
                            logger.error(
                                f"[{self.site_key}] Error fetching job detail ({job_data['url']}): {e}"
                            )
                            continue

                    # Pagination (FacetWP)
                    # Look for next button
                    next_btn = await page.query_selector(
                        "a.facetwp-page.next, a.next.page-numbers"
                    )
                    if next_btn:
                        logger.info(f"[{self.site_key}] Clicking Next button...")
                        await next_btn.click()
                        await page.wait_for_timeout(5000)
                        page_count += 1
                    else:
                        logger.info(
                            f"[{self.site_key}] No more pages found or pagination not present."
                        )
                        break

            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
            finally:
                await context.close()
                await browser.close()

        return jobs

    async def auto_scroll(self, page):
        """Scroll down to trigger any lazy loading or FacetWP facets"""
        await page.evaluate("""
            async () => {
                await new Promise((resolve) => {
                    let totalHeight = 0;
                    let distance = 100;
                    let timer = setInterval(() => {
                        let scrollHeight = document.body.scrollHeight;
                        window.scrollBy(0, distance);
                        totalHeight += distance;
                        if(totalHeight >= scrollHeight){
                            clearInterval(timer);
                            resolve();
                        }
                    }, 100);
                });
            }
        """)

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
