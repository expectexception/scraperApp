import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class BoeingScraper(BaseScraper):
    """
    Scraper for Boeing Jobs

    Structure:
    - Search page with keyword and location inputs
    - Pagination via "Next" button
    - Job details on separate pages
    - OneTrust cookie banner
    """

    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="boeing", db_manager=db_manager)
        self.base_url = "https://jobs.boeing.com"
        self.search_url = f"{self.base_url}/search-jobs"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Scrape jobs from Boeing (Listing only)
        """
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                logger.info(f"[{self.site_key}] Navigating to {self.search_url}")
                try:
                    await page.goto(
                        self.search_url, wait_until="networkidle", timeout=60000
                    )
                except Exception:
                    pass

                # Cookie banner
                try:
                    accept_btn = await page.wait_for_selector(
                        "#onetrust-accept-btn-handler", timeout=10000
                    )
                    if accept_btn:
                        await accept_btn.click()
                except Exception:
                    pass

                site_config = self.config.get("scrapers", {}).get("boeing", {})
                search_queries = site_config.get("search_queries", []) or [""]
                search_locations = site_config.get("search_locations", []) or [""]

                search_combinations = [
                    (q, l) for q in search_queries for l in search_locations
                ]

                for query, loc in search_combinations:
                    if len(jobs) >= self.max_jobs:
                        break

                    logger.info(
                        f"[{self.site_key}] Search: Keyword='{query}', Location='{loc}'"
                    )
                    direct_url = f"{self.base_url}/search-jobs?k={query}&l={loc}"

                    try:
                        await page.goto(
                            direct_url, wait_until="domcontentloaded", timeout=45000
                        )
                        await self.random_delay(2, 4)

                        page_count = 0
                        while len(jobs) < self.max_jobs:
                            try:
                                await page.wait_for_selector(
                                    "#search-results-list ul li", timeout=10000
                                )
                            except Exception:
                                break

                            job_elements = await page.query_selector_all(
                                "#search-results-list ul li"
                            )
                            logger.info(
                                f"[{self.site_key}] Found {len(job_elements)} jobs on page {page_count + 1}"
                            )

                            for el in job_elements:
                                if len(jobs) >= self.max_jobs:
                                    break
                                try:
                                    link = await el.query_selector(
                                        "a.search-results__job-link"
                                    )
                                    if not link:
                                        continue

                                    title = await link.inner_text()
                                    url_suffix = await link.get_attribute("href")
                                    job_url = (
                                        self.base_url + url_suffix
                                        if url_suffix.startswith("/")
                                        else url_suffix
                                    )

                                    loc_el = await el.query_selector(
                                        ".search-results__job-info.location"
                                    )
                                    location = (
                                        await loc_el.inner_text()
                                        if loc_el
                                        else "Unknown"
                                    )

                                    import re as _re

                                    job_id_match = _re.search(
                                        r"/(\d+)(?:[/?]|$)", url_suffix or ""
                                    )
                                    job_id = (
                                        job_id_match.group(1)
                                        if job_id_match
                                        else f"boeing_{len(jobs) + 1}"
                                    )

                                    jobs.append(
                                        {
                                            "job_id": f"boeing_{job_id}",
                                            "company": self.company_name,
                                            "title": title.strip(),
                                            "location": location.strip(),
                                            "url": job_url,
                                            "source_url": job_url,
                                            "apply_url": job_url,
                                        }
                                    )
                                except Exception:
                                    continue

                            if len(jobs) >= self.max_jobs:
                                break

                            next_btn = await page.query_selector(
                                "a.next:not(.disabled)"
                            )
                            if next_btn:
                                await next_btn.click()
                                await page.wait_for_load_state("networkidle")
                                page_count += 1
                                await asyncio.sleep(2)
                            else:
                                break
                    except Exception as e:
                        logger.warning(
                            f"[{self.site_key}] Search combination failed: {e}"
                        )
                        continue

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
                    desc_el = await page.query_selector(
                        "div.ats-description"
                    ) or await page.query_selector("main")
                    job["description"] = await desc_el.inner_html() if desc_el else ""
                except Exception as e:
                    logger.warning(
                        f"[{self.site_key}] Failed to load description for {job['url']}: {e}"
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
