import asyncio
import logging
import re
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from .job_schema import get_job_dict
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class DeltaScraper(BaseScraper):
    """Scraper for Delta Airlines careers site using Avature portal via Playwright."""

    def __init__(self, config: Dict, db_manager=None):
        super().__init__(config, site_key="delta", db_manager=db_manager)
        self.base_url = "https://delta.avature.net/en_US/careers/SearchJobs/"
        self.detail_api_url = "https://delta.avature.net/en_US/careers/ViewJob?jobId="

    async def fetch_jobs(self) -> List[Dict]:
        """Fetch jobs by paginating through search results using Playwright."""
        jobs = []
        offset = 0
        limit = 10
        max_jobs_to_reach = self.max_jobs or 50

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                # Keep going until we reach limits or no more jobs
                while len(jobs) < max_jobs_to_reach and offset < 2000:
                    # Use query parameter for pagination
                    target_url = f"{self.base_url}?listFilterMode=1&jobOffset={offset}"
                    logger.info(f"[{self.site_key}] Navigating to {target_url}...")

                    await page.goto(target_url, wait_until="networkidle", timeout=60000)

                    # Check for 'No jobs found'
                    content = await page.content()
                    if "No jobs found" in content or "1-0 of" in content:
                        logger.info(
                            f"[{self.site_key}] Reached end of results at offset {offset}"
                        )
                        break

                    # Wait for items to load
                    try:
                        await page.wait_for_selector(".list__item", timeout=15000)
                    except:
                        logger.info(
                            f"[{self.site_key}] No job items found at offset {offset}"
                        )
                        break

                    items = await page.query_selector_all(".list__item")
                    if not items:
                        break

                    logger.info(
                        f"[{self.site_key}] Found {len(items)} job items at offset {offset}"
                    )

                    for item in items:
                        if len(jobs) >= max_jobs_to_reach:
                            break

                        title_el = await item.query_selector(
                            ".list__item__text__title a"
                        )
                        if not title_el:
                            continue

                        title = await title_el.inner_text()
                        title = title.strip()
                        href = await title_el.get_attribute("href")

                        if not title or not href:
                            continue

                        job_url = (
                            href
                            if href.startswith("http")
                            else f"https://delta.avature.net{href}"
                        )

                        # Extract jobId from href using regex
                        # Format: /en_US/careers/JobDetail/Title/12345 or ?jobId=12345
                        job_id = ""
                        id_match = re.search(r"/(\d+)(\?|$)", href)
                        if id_match:
                            job_id = id_match.group(1)
                        else:
                            # Try query param
                            query_match = re.search(r"jobId=(\d+)", href)
                            if query_match:
                                job_id = query_match.group(1)

                        # Early filtering
                        if not self.should_process_job(title):
                            continue

                        if await self.is_url_already_scraped(job_url):
                            continue

                        location = "Unknown"
                        loc_el = await item.query_selector(
                            ".list__item__text__subtitle span:first-child"
                        )
                        if loc_el:
                            location = await loc_el.inner_text()
                            location = location.strip()

                        # Fetch description via API (more efficient)
                        desc = "Description not available"
                        if job_id:
                            desc = await self.fetch_job_description_api(job_id)

                        job = get_job_dict(
                            job_id=f"{self.site_key}_{hash(job_url)}",
                            title=title,
                            company=self.company_name,
                            location=location,
                            url=job_url,
                            source_url=self.base_url if hasattr(self, 'base_url') else job_url,
                            description=desc,
                            apply_url=job_url,
                            source=self.site_key
                        )
                        jobs.append(job)
                        logger.info(
                            f"[{self.site_key}] Successfully extracted: {title}"
                        )

                    if len(items) < limit:
                        break

                    offset += limit

                return jobs

            except Exception as e:
                logger.error(f"[{self.site_key}] Scraper execution failed: {e}")
                return jobs
            finally:
                await browser.close()

    async def fetch_job_description_api(self, job_id: str) -> str:
        """Fetch job description HTML from the ViewJob endpoint directly."""
        try:
            url = f"{self.detail_api_url}{job_id}"

            def fetch():
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "X-Requested-With": "XMLHttpRequest",
                }
                return requests.get(url, headers=headers, timeout=15)

            response = await asyncio.to_thread(fetch)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                # Look for the content within the partial HTML
                content = soup.select_one(
                    '.description-ajax, .article__content, [itemprop="description"]'
                )
                if content:
                    return str(content)
                return response.text

            return "Description not available"
        except Exception as e:
            logger.error(f"[{self.site_key}] Error fetching description API: {e}")
            return "Description error"

    async def run(self):
        """Standard run flow."""
        self.print_header()

        jobs = await self.fetch_jobs()

        matched_jobs, rejected_jobs, stats = self.apply_title_filter(jobs)
        await self.save_results(matched_jobs)

        return matched_jobs
