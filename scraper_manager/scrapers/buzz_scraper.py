import logging
from playwright.async_api import async_playwright
import re

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class BuzzScraper(BaseScraper):
    """
    Scraper for Buzz (Ryanair Group Careers)
    URL: https://careers.ryanair.com/search/#job/search
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="buzz", db_manager=db_manager)
        self.base_url = "https://careers.ryanair.com/search/#job/search"
        self.company_name = "Buzz (Ryanair Group)"

    async def fetch_jobs(self) -> list:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                # Navigate directly to search results for "Buzz"
                # This is more robust than trying to interact with the SPA search box
                target_url = "https://careers.ryanair.com/jobs/?title=Buzz&ryanair-jobs-department=&ryanair-jobs-location="
                logger.info(f"[{self.site_key}] Navigating directly to: {target_url}")

                try:
                    await page.goto(target_url, wait_until="networkidle", timeout=60000)
                    await self.random_delay(3, 5)
                except Exception as e:
                    logger.error(f"[{self.site_key}] Navigation to results failed: {e}")
                    return []

                # Wait for the job list to load
                try:
                    await page.wait_for_selector(
                        "li.job, .content__jobs", timeout=15000
                    )
                except Exception:
                    logger.warning(f"[{self.site_key}] Timeout waiting for job list")

                # Scroll to ensure all jobs are loaded
                await self.scroll_to_bottom(page)
                await self.random_delay(2, 3)

                # We extract links using the specific selector for Ryanair portal results
                links = await page.evaluate("""() => {
                    const jobElements = document.querySelectorAll('li.job h2.job__title a, a.job-title, .job-item a');
                    return Array.from(jobElements).map(a => ({
                        t: a.innerText.trim(), 
                        h: a.href
                    }));
                }""")

                logger.info(f"[{self.site_key}] Found {len(links)} potential job links")

                seen_urls = set()
                job_urls = []
                for link in links:
                    href = link["h"]
                    title = link["t"]
                    if href and href not in seen_urls and self.is_job_link(title, href):
                        seen_urls.add(href)
                        job_urls.append((href, title))

                logger.info(
                    f"[{self.site_key}] Found {len(job_urls)} relevant job links"
                )

                for i, (url, title) in enumerate(job_urls):
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    try:
                        if not self.should_process_job(title):
                            continue

                        if await self.is_url_already_scraped(url):
                            continue

                        logger.info(f"[{self.site_key}] Fetching details for: {url}")
                        detail_page = await context.new_page()
                        await detail_page.goto(
                            url, wait_until="domcontentloaded", timeout=30000
                        )
                        await detail_page.wait_for_timeout(2000)

                        real_title = title
                        h1 = detail_page.locator("h1").first
                        if await h1.is_visible():
                            extracted = await h1.inner_text()
                            if len(extracted) > 5:
                                real_title = extracted

                        description = ""
                        for loc in [
                            "main",
                            "article",
                            ".job-description",
                            ".content",
                            '[data-ui="job-description"]',
                        ]:
                            elem = detail_page.locator(loc).first
                            try:
                                if await elem.is_visible():
                                    description = await elem.inner_html()
                                    break
                            except:
                                continue

                        if not description:
                            description = await self.extract_description_from_page(
                                detail_page
                            )

                        location = "Europe"
                        posted_date = await self.extract_posted_date_from_page(
                            detail_page
                        )

                        job_id = f"buzz_{i + 1}"
                        match = re.search(r"j/([A-Z0-9]+)", url)
                        if match:
                            job_id = f"buzz_{match.group(1)}"

                        job = get_job_dict(
                            job_id=job_id,
                            title=real_title,
                            company=self.company_name,
                            location=location,
                            url=url,
                            source_url=url,
                            description=description,
                            apply_url=url,
                            posted_date=posted_date,
                            source=self.site_key,
                        )

                        jobs.append(job)
                        await detail_page.close()

                    except Exception as e:
                        logger.error(
                            f"[{self.site_key}] Error parsing job {i} ({url}): {e}"
                        )
                        continue

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
