import logging
import re
from datetime import datetime
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class AirCanadaScraper(BaseScraper):
    """Scraper for Air Canada (Phenom People)"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="air_canada", db_manager=db_manager)
        self.site_config = config.get("sites", {}).get("air_canada", {})
        self.base_url = "https://careers.aircanada.com"
        self.jobs_url = "https://careers.aircanada.com/ca/en/search-results"
        self.company_name = "Air Canada"

    async def fetch_jobs(self) -> list:
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                logger.info(f"[{self.site_key}] Loading jobs from {self.jobs_url}")
                await page.goto(self.jobs_url, wait_until="domcontentloaded", timeout=60000)
                
                # Wait for any job link to appear
                try:
                    await page.wait_for_selector('a[href*="/job/"]', timeout=30000)
                except Exception:
                    logger.warning(f"[{self.site_key}] Timeout waiting for job links")
                
                await self.random_delay(3, 5)
                
                # Phenom usually loads multiple pages via "load more" or just extracts visible
                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll("a")).map(a => ({
                        href: a.href,
                        text: a.innerText || a.textContent
                    }));
                }''')
                
                seen = set()
                for link in links:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    href = link.get("href", "")
                    if not href or "/job/" not in href.lower():
                        continue
                        
                    text_parts = link.get("text", "").strip().split("\\n")
                    if not text_parts or len(text_parts[0]) < 3:
                        continue
                        
                    title = text_parts[0].strip()
                    if title.lower() in ["read more", "apply", "apply now", "save job"]:
                        continue
                        
                    job_url = href if href.startswith("http") else self.base_url.rstrip("/") + "/" + href.lstrip("/")
                    
                    if job_url in seen:
                        continue
                    seen.add(job_url)
                    
                    # Extract location from text if possible
                    location = "Unknown"
                    if len(text_parts) > 1:
                        for part in text_parts[1:]:
                            if len(part) > 2 and "Category" not in part and "Posted" not in part:
                                location = part.strip()
                                break
                                
                    job_id = f"aircanada_{abs(hash(job_url)) % 10000000}"
                    
                    jobs.append({
                        "job_id": job_id,
                        "title": title,
                        "company": self.company_name,
                        "source": self.site_key,
                        "url": job_url,
                        "apply_url": job_url,
                        "location": location,
                        "timestamp": datetime.now().isoformat(),
                        "description": ""
                    })
                    
            except Exception as e:
                logger.error(f"[{self.site_key}] Extraction failed: {e}")
            finally:
                await context.close()
                await browser.close()
                
        return jobs

    async def fetch_job_descriptions(self, jobs: list) -> list:
        if not jobs:
            return jobs
            
        logger.info(f"[{self.site_key}] Fetching descriptions for {len(jobs)} jobs...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            for job in jobs:
                try:
                    page, context = await self.setup_stealth_page(browser)
                    await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
                    
                    # Try generic description selectors
                    desc = ""
                    selectors = [".job-description", ".ph-job-description", "article", "main"]
                    for sel in selectors:
                        el = await page.query_selector(sel)
                        if el:
                            text = await el.inner_text()
                            if len(text) > 200:
                                desc = text.strip()
                                break
                    if not desc:
                        desc = await self.extract_description_from_page(page)
                        
                    job["description"] = desc
                    await context.close()
                except Exception as e:
                    logger.warning(f"[{self.site_key}] Failed to fetch description for {job['url']}: {e}")
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
