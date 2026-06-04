import logging
import re
from urllib.parse import urljoin
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class CargoluxScraper(BaseScraper):
    """
    Scraper for Cargolux (PeopleClick)
    URL: https://careers.peopleclick.eu.com/careerscp/client_cargolux/external/search/search.html
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="cargolux", db_manager=db_manager)
        self.base_url = "https://careers.peopleclick.eu.com/careerscp/client_cargolux/external/search/search.html"
        self.company_name = "Cargolux"

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
                await page.wait_for_timeout(5000)

                # Some PeopleClick sites need an initial click/search
                # ID identified: sp-searchButton
                search_btn = await page.query_selector(
                    '#sp-searchButton, input[type="button"][value="Search"]'
                )
                if search_btn:
                    logger.info(
                        f"[{self.site_key}] Clicking Search button to load all jobs..."
                    )
                    await search_btn.click()
                    # Wait for results to appear
                    try:
                        await page.wait_for_selector(".pf-srp-singlehit", timeout=15000)
                    except:
                        logger.warning(
                            f"[{self.site_key}] Timeout waiting for .pf-srp-singlehit after click."
                        )
                else:
                    logger.warning(
                        f"[{self.site_key}] Search button not found, attempting to wait for results anyway."
                    )

                page_count = 1
                while True:
                    if self.max_pages and page_count > self.max_pages:
                        break

                    logger.info(f"[{self.site_key}] Processing page {page_count}...")

                    # Wait for results
                    try:
                        await page.wait_for_selector(
                            ".pf-srp-singlehit, .pf-srp-jobResult", timeout=15000
                        )
                    except:
                        logger.warning(
                            f"[{self.site_key}] No jobs found on page {page_count}"
                        )
                        break

                    job_rows = await page.query_selector_all(
                        ".pf-srp-singlehit, .pf-srp-jobResult"
                    )
                    if not job_rows:
                        break

                    logger.info(
                        f"[{self.site_key}] Found {len(job_rows)} job rows on page {page_count}"
                    )

                    page_jobs_data = []
                    for row in job_rows:
                        try:
                            title_el = await row.query_selector(
                                "a.pf-srp-jobResult-title, .pf-srp-jobResult-title a"
                            )
                            if not title_el:
                                continue

                            title = await title_el.inner_text()
                            url = await title_el.get_attribute("href")
                            if url:
                                url = urljoin(self.base_url, url)

                            # Clean Title (remove any leading/trailing whitespace)
                            title = title.strip()

                            # Extract Location and Job ID from the row content
                            row_text = await row.inner_text()

                            location = "Luxembourg"  # Default for Cargolux
                            loc_match = re.search(r"Location:\s*([^\n\r]+)", row_text)
                            if loc_match:
                                location = loc_match.group(1).strip()

                            req_id = ""
                            id_match = re.search(r"Job ID:\s*([^\n\r]+)", row_text)
                            if id_match:
                                req_id = id_match.group(1).strip()
                            else:
                                # Fallback to URL parsing if ID not in text
                                id_url_match = re.search(r"jobPostId=(\d+)", url)
                                if id_url_match:
                                    req_id = id_url_match.group(1)

                            page_jobs_data.append(
                                {
                                    "title": title,
                                    "url": url,
                                    "location": location,
                                    "req_id": req_id,
                                }
                            )
                        except Exception as e:
                            logger.error(f"[{self.site_key}] Error parsing row: {e}")
                            continue

                    # Visit each job detail page
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

                            # PeopleClick descriptions are usually in a specific container
                            desc_el = await detail_page.query_selector(
                                ".pf-job-post-content, #pf-job-description, .pf-description"
                            )
                            description = ""
                            if desc_el:
                                description = await desc_el.inner_text()
                            else:
                                description = await self.extract_description_from_page(
                                    detail_page
                                )

                            job = get_job_dict(
                                job_id=f"cargolux_{job_data['req_id']}",
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

                    # Pagination
                    try:
                        next_btn = await page.query_selector(
                            'a[title="Next"], .pf-srp-pagination-next'
                        )
                        if next_btn:
                            logger.info(f"[{self.site_key}] Clicking Next button...")
                            await next_btn.click()
                            await page.wait_for_timeout(5000)
                            page_count += 1
                        else:
                            logger.info(f"[{self.site_key}] No more pages found.")
                            break
                    except Exception as e:
                        logger.error(
                            f"[{self.site_key}] Error navigating to next page: {e}"
                        )
                        break

            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
            finally:
                await context.close()
                await browser.close()

        return jobs

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
