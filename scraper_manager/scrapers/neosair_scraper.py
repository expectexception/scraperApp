import asyncio
import logging
from typing import List, Dict
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class NeosAirScraper(BaseScraper):
    """
    Scraper for Neos Air
    URL: https://www.neosair.com/en/work-with-us/open-positions
    """

    def __init__(self, config: Dict, db_manager=None):
        super().__init__(config, site_key="neosair", db_manager=db_manager)
        self.base_url = "https://www.neosair.com"
        self.jobs_url = "https://www.neosair.com/en/work-with-us/open-positions"
        self.company_name = "Neos Air"

    async def fetch_jobs(self) -> List[Dict]:
        jobs = []

        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                logger.info(f"[{self.site_key}] Navigating to {self.jobs_url}")
                await page.goto(self.jobs_url, wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(3000)

                # Look for links
                job_elements = await page.query_selector_all("a[href*='/work-with-us/']")
                
                seen_urls = set()
                
                for el in job_elements:
                    href = await el.get_attribute("href")
                    if not href or "open-positions" in href:
                        continue
                    
                    full_url = href if href.startswith("http") else f"{self.base_url}{href}"
                    
                    if full_url in seen_urls:
                        continue
                        
                    title = await el.text_content()
                    title = title.strip() if title else "Unknown"
                    if not title or title.lower() in ["read more", "apply", "details"]:
                        continue
                        
                    seen_urls.add(full_url)
                    
                    jobs.append({
                        "company": self.company_name,
                        "title": title,
                        "location": "Italy", # Default for Neos
                        "url": full_url,
                        "source_url": full_url,
                        "apply_url": full_url,
                        "is_active": True,
                    })

            except Exception as e:
                logger.error(f"[{self.site_key}] Error fetching jobs: {e}")
            finally:
                await context.close()
                await browser.close()

        return jobs

    async def fetch_job_descriptions(self, jobs: List[Dict]) -> List[Dict]:
        if not jobs:
            return []

        logger.info(f"[{self.site_key}] Fetching descriptions for {len(jobs)} jobs...")
        
        from playwright.async_api import async_playwright

        enriched_jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            for job in jobs:
                try:
                    await page.goto(job["url"], wait_until="networkidle", timeout=30000)
                    
                    # Try to find description content
                    desc_text = ""
                    content_el = await page.query_selector("main") or await page.query_selector("body")
                    if content_el:
                        desc_text = await content_el.inner_text()
                    
                    job_dict = get_job_dict(
                        job_id=f"{self.site_key}_{hash(job['url'])}",
                        title=job["title"],
                        company=self.company_name,
                        location=job["location"],
                        url=job["url"],
                        source_url=self.jobs_url,
                        description=desc_text,
                        apply_url=job["url"],
                        source=self.site_key
                    )
                    enriched_jobs.append(job_dict)

                except Exception as e:
                    logger.warning(f"[{self.site_key}] Failed to fetch details for {job['url']}: {e}")
                
                await asyncio.sleep(1)
                
            await context.close()
            await browser.close()

        return enriched_jobs

    async def run(self):
        self.print_header()

        jobs = await self.fetch_jobs()
        if not jobs:
            return []

        # Filter by title
        matched_jobs, rejected_jobs, stats = self.apply_title_filter(jobs)
        if not matched_jobs:
            return []

        # Filter out already scraped
        new_jobs, _ = await self.filter_new_jobs(matched_jobs)
        if not new_jobs:
            return []

        # Fetch details
        final_jobs = await self.fetch_job_descriptions(new_jobs)
        await self.save_results(final_jobs)
        return final_jobs
