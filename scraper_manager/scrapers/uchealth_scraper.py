import asyncio
import logging
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class UCHealthScraper(BaseScraper):
    """
    Scraper for UCHealth Careers
    URL: https://careers.uchealth.org/search/jobs
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="uchealth", db_manager=db_manager)
        self.base_url = "https://careers.uchealth.org/search/jobs"
        self.company_name = "UCHealth"

    async def fetch_jobs(self) -> list:
        jobs = []
        # Search queries to target relevant jobs
        queries = ["flight", "dispatcher", "paramedic", "lifeline"]
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                for q in queries:
                    search_url = f"{self.base_url}?q={q}"
                    logger.info(f"[{self.site_key}] Searching UCHealth with query '{q}': {search_url}")
                    
                    try:
                        await page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
                        await page.wait_for_timeout(3000)
                        
                        # Wait for job items to load
                        await page.wait_for_selector(".jobs-section__item", timeout=10000)
                    except Exception as e:
                        logger.warning(f"[{self.site_key}] Query '{q}' timed out or returned no results: {e}")
                        continue

                    # Parse results
                    html = await page.content()
                    soup = BeautifulSoup(html, "html.parser")
                    job_items = soup.find_all(class_="jobs-section__item")
                    logger.info(f"[{self.site_key}] Found {len(job_items)} items for query '{q}'")

                    for item in job_items:
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break

                        # Title and Link
                        title_link = item.find("a", href=True)
                        if not title_link:
                            continue
                        
                        title = title_link.text.strip()
                        href = title_link.get("href")
                        if not href:
                            continue
                        
                        url = href if href.startswith("http") else f"https://careers.uchealth.org{href}"

                        # Location & meta
                        # Usually format: "Loveland • Administrative/Clerical Support • Full Time • 391596"
                        meta_text = item.text.strip()
                        location = "Colorado, US"
                        if "•" in meta_text:
                            parts = [p.strip() for p in meta_text.split("•")]
                            # The title is in meta_text too, so extract location from the line below title
                            # Let's find parts and use the first non-title part as location
                            for part in parts:
                                if part and title not in part and len(part) < 50:
                                    location = part
                                    break

                        # Unique job ID
                        job_id = "uchealth_" + re.sub(r"\W+", "_", title).lower()
                        match = re.search(r"\d{5,}", meta_text)
                        if match:
                            job_id = f"uchealth_{match.group(0)}"

                        jobs.append(
                            {
                                "company": self.company_name,
                                "title": title,
                                "location": location,
                                "url": url,
                                "source_url": search_url,
                                "apply_url": url,
                                "is_active": True,
                                "job_seq_no": job_id,
                            }
                        )

            except Exception as e:
                logger.error(f"[{self.site_key}] Global error during job fetching: {e}")
            finally:
                await context.close()
                await browser.close()

        # Deduplicate jobs by URL
        seen_urls = set()
        deduped_jobs = []
        for j in jobs:
            if j["url"] not in seen_urls:
                seen_urls.add(j["url"])
                deduped_jobs.append(j)
        return deduped_jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        if not jobs:
            return []

        logger.info(
            f"[{self.site_key}] Fetching descriptions for {len(jobs)} matched jobs..."
        )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            for job in jobs:
                url = job["url"]
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(2000)
                    html = await page.content()
                    soup = BeautifulSoup(html, "html.parser")

                    # Extract description
                    desc_container = (
                        soup.find(class_="job-description")
                        or soup.find(class_="job-details")
                        or soup.find("body")
                    )
                    
                    if desc_container:
                        text = desc_container.text
                        text = re.sub(r"\s+", " ", text).strip()
                        job["description"] = text
                        # Backfill location from the original posting when missing.
                        if not job.get("location") or job.get("location") == "Unknown":
                            _loc = await self.extract_location_from_page(page)
                            if _loc:
                                job["location"] = _loc
                    else:
                        job["description"] = ""
                except Exception as e:
                    logger.warning(
                        f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}"
                    )

            await context.close()
            browser.close()

        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        if not jobs:
            return []

        if self.use_filter and self.filter_manager:
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)
            if not jobs:
                return []

        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []

        jobs = await self.fetch_job_descriptions(jobs)
        
        # Build get_job_dict objects
        final_jobs = []
        for j in jobs:
            final_jobs.append(
                get_job_dict(
                    job_id=j.pop("job_seq_no"),
                    title=j["title"],
                    company=self.company_name,
                    location=j["location"],
                    url=j["url"],
                    source_url=j["source_url"],
                    description=j.get("description", ""),
                    apply_url=j["apply_url"],
                    source=self.site_key,
                )
            )

        await self.save_results(final_jobs)
        return final_jobs
