import asyncio
import logging
import re
from typing import List, Dict, Any
from urllib.parse import urljoin
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class TravelcoupScraper(BaseScraper):
    """
    Scraper for Travelcoup
    URL: https://www.travelcoup.com/careers
    """

    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="travelcoup", db_manager=db_manager)
        self.base_url = "https://www.travelcoup.com/careers"
        self.company_name = "Travelcoup"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            try:
                page, context = await self.setup_stealth_page(browser)
                
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(3000)

                # Extract jobs directly from the grid list using JS
                extracted_jobs = await page.evaluate('''() => {
                    const links = Array.from(document.querySelectorAll('a.group'));
                    return links.map(a => {
                        const href = a.getAttribute('href') || "";
                        const titleEl = a.querySelector('.text-primary-content');
                        const title = titleEl ? titleEl.innerText.trim() : "";
                        
                        // Extract locations
                        const locSpans = Array.from(a.querySelectorAll('span.bg-gray-200'));
                        const location = locSpans.map(s => s.innerText.trim()).join(", ");
                        
                        return { title, href, location };
                    }).filter(j => j.title && j.href);
                }''')

                logger.info(f"[{self.site_key}] Found {len(extracted_jobs)} job postings on Careers page")

                for job_data in extracted_jobs:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    title = job_data["title"]
                    # Convert relative URL to absolute URL
                    url = urljoin(self.base_url, job_data["href"])
                    location = job_data["location"] or "Unknown"

                    if not self.should_process_job(title):
                        continue

                    # Extract job_id from href slug
                    slug = job_data["href"].strip("/")
                    job_id = f"travelcoup_{slug}" if slug else f"travelcoup_{hash(url)}"

                    job = {
                        "job_id": job_id,
                        "title": title,
                        "company": self.company_name,
                        "source": self.site_key,
                        "url": url,
                        "apply_url": url,
                        "location": location,
                    }

                    jobs.append(job)

            except Exception as e:
                logger.error(f"[{self.site_key}] Global error in fetch_jobs: {e}")
            finally:
                if 'context' in locals():
                    await context.close()
                await browser.close()
                
        return jobs

    async def fetch_job_descriptions(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not jobs:
            return []
            
        logger.info(f"[{self.site_key}] Fetching descriptions for {len(jobs)} jobs...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            try:
                for job in jobs:
                    page, context = await self.setup_stealth_page(browser)
                    try:
                        await page.goto(job["url"], wait_until="networkidle", timeout=30000)
                        await page.wait_for_timeout(2000)

                        body_text = await page.locator("body").inner_text()
                        
                        # Clean up the body text to get the actual description
                        desc = body_text
                        if "Login" in desc:
                            parts = desc.split("Login\n")
                            if len(parts) > 1:
                                desc = parts[1]
                                
                        for marker in ["✕", "Login\nKunden Login", "TRAVELCOUP", "Über uns"]:
                            if marker in desc:
                                desc = desc.split(marker)[0]
                                
                        job["description"] = desc.strip()[:4000]

                    except Exception as e:
                        logger.warning(f"[{self.site_key}] Failed to fetch description for {job['title']}: {e}")
                    finally:
                        await context.close()
            finally:
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
