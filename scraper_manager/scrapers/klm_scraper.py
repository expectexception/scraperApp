import logging
import re
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class KLMScraper(BaseScraper):
    """
    Scraper for KLM Royal Dutch Airlines.
    Uses Playwright with headful mode support for WAF bypass.
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="klm", db_manager=db_manager)
        self.base_url = "https://careers.klm.com/en/jobs/?page=1"
        self.company_name = "KLM Royal Dutch Airlines"

    async def fetch_jobs(self) -> list:
        logger.info(
            f"[{self.site_key}] Navigating to {self.base_url} (Headless={self.headless})..."
        )
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-http2",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            page, context = await self.setup_stealth_page(browser)

            try:
                # Use a longer timeout and wait for content
                await page.goto(
                    self.base_url, wait_until="domcontentloaded", timeout=90000
                )
                await self.random_delay(5, 8)  # Give it time to render the SPA
                await self.simulate_human_behavior(page)

                # KLM jobs follow the pattern: https://careers.klm.com/en/jobs/[slug]/[id]/
                links = await page.evaluate(r"""() => {
                    const jobLinks = [];
                    // The subagent found: a[href^="/en/jobs/"] span
                    document.querySelectorAll('a[href*="/en/jobs/"]').forEach(a => {
                        const href = a.href;
                        // Titles are often in a span inside the link
                        const span = a.querySelector('span');
                        const text = (span ? span.innerText : a.innerText || '').trim();
                        
                        // Pattern: includes /en/jobs/ and ends with a numeric ID segment
                        if (href && href.match(/\/jobs\/[^\/]+\/\d+\/?$/)) {
                             jobLinks.push({t: text, h: href});
                        }
                    });
                    return jobLinks;
                }""")

                logger.info(f"[{self.site_key}] Found {len(links)} potential job links")

                seen_urls = set()
                initial_jobs = []
                for link in links:
                    href = link["h"]
                    title = link["t"]

                    if (
                        href
                        and href not in seen_urls
                        and title
                        and self.is_job_link(title, href)
                    ):
                        # Filter out common false positives
                        forbidden_titles = {
                            "jobs",
                            "careers",
                            "home",
                            "search",
                            "login",
                            "apply",
                            "view all",
                        }
                        if title.lower() in forbidden_titles:
                            continue

                        seen_urls.add(href)
                        initial_jobs.append({"title": title, "url": href})

                logger.info(
                    f"[{self.site_key}] Found {len(initial_jobs)} potential jobs. Applying pre-filter..."
                )

                # PRE-FILTER: Filter by title first to skip irrelevant roles COMPLETELY
                matched_initial, _, _ = self.apply_title_filter(initial_jobs)

                logger.info(
                    f"[{self.site_key}] {len(matched_initial)} jobs passed pre-filtering. Fetching details..."
                )

                for i, j_initial in enumerate(matched_initial):
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    url = j_initial["url"]
                    title = j_initial["title"]

                    try:
                        if not self.should_process_job(title):
                            continue

                        if await self.is_url_already_scraped(url):
                            continue

                        logger.info(f"[{self.site_key}] Fetching details for: {url}")
                        detail_page = await context.new_page()
                        # Increased timeout for stability
                        await detail_page.goto(url, wait_until="load", timeout=60000)
                        await self.random_delay(1, 2)

                        description = await self.extract_description_from_page(
                            detail_page
                        )

                        job_id = (
                            f"{self.site_key}_{re.sub(r'[^a-zA-Z0-9]', '', url)[-10:]}"
                        )

                        job = get_job_dict(
                            job_id=job_id,
                            title=title,
                            company=self.company_name,
                            location="Various",
                            url=url,
                            source_url=self.base_url,
                            description=description,
                            source=self.site_key,
                        )
                        jobs.append(job)
                        await detail_page.close()
                    except Exception as e:
                        logger.warning(
                            f"[{self.site_key}] Error detail page {url}: {e}"
                        )

            except Exception as e:
                logger.error(f"[{self.site_key}] Main page error: {e}")
            finally:
                await context.close()
                await browser.close()

        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()

        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
