import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright
import requests

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class JetflyScraper(BaseScraper):
    """
    Scraper for Jetfly (BambooHR)
    URL: https://jetfly.bamboohr.com/careers
    """
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="jetfly", db_manager=db_manager)
        self.api_url = "https://jetfly.bamboohr.com/careers/list"
        self.base_url = "https://jetfly.bamboohr.com/careers"
        self.company_name = "Jetfly"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        logger.info(f"[{self.site_key}] Querying BambooHR API...")
        try:
            resp = await asyncio.to_thread(requests.get, self.api_url, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("result", [])
                
                for item in results:
                    if self.max_jobs and len(jobs) >= self.max_jobs: break
                    
                    job_id = item.get("id")
                    title = item.get("jobOpeningName")
                    
                    if not job_id or not title: continue
                    
                    url = f"{self.base_url}/{job_id}"
                    
                    loc_dict = item.get("location", {})
                    city = loc_dict.get("city", "") if loc_dict else ""
                    state = loc_dict.get("state", "") if loc_dict else ""
                    location = f"{city}, {state}".strip(", ") if city or state else "Unknown"
                    
                    jobs.append({
                        "job_id": f"jetfly_{job_id}",
                        "title": title,
                        "company": self.company_name,
                        "source": self.site_key,
                        "url": url,
                        "apply_url": url,
                        "location": location,
                    })
        except Exception as e:
            logger.error(f"[{self.site_key}] Failed to fetch jobs: {e}")
            
        logger.info(f"[{self.site_key}] Found {len(jobs)} jobs")
        return jobs

    async def fetch_job_descriptions(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not jobs: return []
        logger.info(f"[{self.site_key}] Fetching details for {len(jobs)} jobs...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            
            for job in jobs:
                try:
                    page, context = await self.setup_stealth_page(browser)
                    await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(2000)
                    
                    # BambooHR stores description in a script tag or div
                    desc = ""
                    try:
                        div = await page.wait_for_selector(".jss-html-container, .job-description, [data-testid='JobDescription']", timeout=5000)
                        if div:
                            desc = await div.inner_text()
                    except:
                        pass
                        
                    if not desc:
                        desc = await self.extract_description_from_page(page)
                        
                    job["description"] = desc
                    # Backfill location from the original posting when missing.
                    if not job.get("location") or job.get("location") == "Unknown":
                        _loc = await self.extract_location_from_page(page)
                        if _loc:
                            job["location"] = _loc
                    
                except Exception as e:
                    logger.warning(f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}")
                finally:
                    await context.close()
                await asyncio.sleep(0.5)
            await browser.close()
            
        return jobs

    async def run(self):
        self.print_header()
        jobs_raw = await self.fetch_jobs()
        jobs = [get_job_dict(**job) for job in jobs_raw]
        if not jobs: return []
        if self.use_filter and self.filter_manager:
            jobs, _, _ = self.apply_title_filter(jobs)
            if not jobs: return []
        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs: return []
        jobs = await self.fetch_job_descriptions(jobs)
        await self.save_results(jobs)
        return jobs
