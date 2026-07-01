import asyncio
import logging
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class SkyWestScraper(BaseScraper):
    """
    Scraper for SkyWest Airlines (Phenom People frontend / iCIMS backend)
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="skywest", db_manager=db_manager)
        self.base_url = "https://jobs.skywest.com/skywest-airlines/jobs"
        self.company_name = "SkyWest Airlines"

    async def fetch_jobs(self) -> list:
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                # We will check the first 3 pages to get recent postings
                for page_num in range(1, 4):
                    url = f"{self.base_url}?page={page_num}&sortBy=relevance"
                    logger.info(f"[{self.site_key}] Navigating to page {page_num}: {url}")
                    
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                        await page.wait_for_timeout(3000)
                    except Exception as e:
                        logger.error(f"[{self.site_key}] Error loading page {page_num}: {e}")
                        break

                    # Check if "could not find any matching jobs" is present
                    body_text = await page.inner_text("body")
                    if "could not find any matching jobs" in body_text.lower():
                        logger.info(f"[{self.site_key}] No more jobs found (reached end of list).")
                        break

                    # Extract job links
                    links = await page.evaluate('''() => {
                        return Array.from(document.querySelectorAll("a")).map(a => ({
                            href: a.href,
                            text: a.innerText || a.textContent
                        }));
                    }''')

                    page_jobs_count = 0
                    for link in links:
                        href = link.get("href", "")
                        text = link.get("text", "").strip()
                        
                        # Match job details links like /skywest-airlines/jobs/12345
                        if href and re.search(r"/skywest-airlines/jobs/\d+", href):
                            if not text or text.lower() in ["read more", "apply", "apply now", "view details"]:
                                continue
                                
                            # Avoid duplicates on the same page/run
                            if any(j["url"] == href for j in jobs):
                                continue

                            job_id = "skywest_" + href.split("/jobs/")[-1].split("?")[0]
                            
                            jobs.append({
                                "company": self.company_name,
                                "title": text,
                                "location": "USA",  # Will backfill from details
                                "url": href,
                                "apply_url": href,
                                "source_url": self.base_url,
                                "job_id": job_id,
                                "description": "",  # Will backfill from details
                            })
                            page_jobs_count += 1

                    logger.info(f"[{self.site_key}] Found {page_jobs_count} jobs on page {page_num}")
                    if page_jobs_count == 0:
                        break

            except Exception as e:
                logger.error(f"[{self.site_key}] Error: {e}")
            finally:
                await context.close()
                await browser.close()

        return jobs

    async def fetch_job_descriptions(self, jobs: list) -> list:
        if not jobs:
            return []

        logger.info(f"[{self.site_key}] Fetching descriptions and locations for {len(jobs)} matched jobs...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            for job in jobs:
                try:
                    logger.info(f"[{self.site_key}] Fetching details for {job['title']}...")
                    await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(2000)

                    # Extract description
                    desc_text = ""
                    # Common Phenom People description selectors
                    selectors = [".job-description", ".jd-info", ".description", "[class*='description']"]
                    for sel in selectors:
                        el = await page.query_selector(sel)
                        if el:
                            desc_text = (await el.inner_text()).strip()
                            if len(desc_text) > 100:
                                break

                    if not desc_text:
                        desc_text = await self.extract_description_from_page(page)

                    job["description"] = desc_text

                    # Extract location
                    loc_el = await page.query_selector(".job-location, .location, [class*='location']")
                    if loc_el:
                        loc_text = (await loc_el.inner_text()).strip()
                        if loc_text:
                            # Clean up location text (remove labels like "Location:")
                            loc_text = re.sub(r"^(location|loc):\s*", "", loc_text, flags=re.IGNORECASE).strip()
                            job["location"] = loc_text
                    else:
                        _loc = await self.extract_location_from_page(page)
                        if _loc:
                            job["location"] = _loc

                except Exception as e:
                    logger.warning(f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}")

            await context.close()
            await browser.close()

        return jobs

    async def run(self):
        self.print_header()
        jobs_raw = await self.fetch_jobs()
        jobs = [get_job_dict(**job) for job in jobs_raw]

        if not jobs:
            return []

        if self.use_filter and self.filter_manager:
            jobs, _, _ = self.apply_title_filter(jobs)
            if not jobs:
                return []

        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []

        jobs = await self.fetch_job_descriptions(jobs)
        await self.save_results(jobs)
        return jobs
