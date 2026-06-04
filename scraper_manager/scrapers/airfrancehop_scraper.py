import logging
from playwright.async_api import async_playwright
import re

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class AirFranceHopScraper(BaseScraper):
    """
    Scraper for Air France HOP
    URL: https://www.hop.fr/en/carriere/
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="airfrancehop", db_manager=db_manager)
        self.base_url = "https://www.hop.fr/en/carriere/"
        self.domain = "https://www.hop.fr"
        self.company_name = "Air France HOP"

    async def fetch_jobs(self) -> list:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")

                try:
                    await page.goto(
                        self.base_url, wait_until="networkidle", timeout=60000
                    )
                except Exception as e:
                    logger.error(f"[{self.site_key}] Navigation failed: {e}")
                    return []

                # Links point directly to /en/job-title/
                links = await page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('a'))
                        .map(a => ({t: a.innerText.trim(), h: a.href}))
                        .filter(a => a.h.includes('www.hop.fr/en/') && !a.h.includes('#') && a.h !== 'https://www.hop.fr/en/' && a.h !== 'https://www.hop.fr/en/carriere/' && a.t.length > 5)
                }""")

                logger.info(f"[{self.site_key}] Found {len(links)} potential job links")

                # Filter out non-job links like "Our news", "FAQ", legal pages

                seen_urls = set()
                job_urls = []
                for link in links:
                    href = link["h"]
                    title = link["t"]
                    if href and href not in seen_urls and self.is_job_link(title, href):
                        seen_urls.add(href)
                        job_urls.append((href, title))

                for i, (url, initial_title) in enumerate(job_urls):
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    if not self.should_process_job(initial_title):
                        continue

                    if await self.is_url_already_scraped(url):
                        continue

                    try:
                        logger.info(f"[{self.site_key}] Fetching details for: {url}")
                        detail_page = await context.new_page()
                        await detail_page.goto(
                            url, wait_until="domcontentloaded", timeout=30000
                        )

                        await detail_page.wait_for_timeout(2000)

                        title = initial_title
                        title_loc = detail_page.locator("h1")
                        if (
                            await title_loc.count() > 0
                            and await title_loc.first.is_visible()
                        ):
                            t = await title_loc.first.inner_text()
                            if t and len(t) > 3:
                                title = t

                        title = title.strip()

                        description = ""
                        detail_page.locator(".entry-content, main, article, .content")
                        for loc in [".entry-content", "main", "article", ".content"]:
                            elements = detail_page.locator(loc)
                            if (
                                await elements.count() > 0
                                and await elements.first.is_visible()
                            ):
                                description = await elements.first.inner_html()
                                break

                        if not description:
                            description = await self.extract_description_from_page(
                                detail_page
                            )

                        location = "France"
                        # Try to extract location from title (e.g., "Bouguenais (44)", "Clermont-Ferrand (63)")
                        loc_match = re.search(r"–\s*([^–]+)\s*\(\d+\)", title)
                        if loc_match:
                            location = loc_match.group(1).strip()

                        posted_date = await self.extract_posted_date_from_page(
                            detail_page
                        )

                        job_id = url.strip("/").split("/")[-1]

                        job = get_job_dict(
                            job_id=f"airfrancehop_{job_id}",
                            title=title,
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
