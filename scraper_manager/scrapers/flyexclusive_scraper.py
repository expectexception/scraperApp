import asyncio
import logging
from bs4 import BeautifulSoup
from datetime import datetime
from .base_scraper import BaseScraper
from .job_schema import get_job_dict
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class FlyexclusiveScraper(BaseScraper):
    """Scraper for FlyExclusive (Paycom ATS)"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="flyexclusive", db_manager=db_manager)
        self.site_config = config.get("sites", {}).get("flyexclusive", {})
        self.base_url = "https://www.paycomonline.net"
        self.jobs_url = "https://www.paycomonline.net/v4/ats/web.php/jobs?clientkey=91989CEA70627F35DBDEA57AC03E0A2B"
        self.company_name = "FlyExclusive"

    async def fetch_jobs(self) -> list:
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                logger.info(f"[{self.site_key}] Loading jobs from {self.jobs_url}")
                await page.goto(self.jobs_url, wait_until="networkidle", timeout=60000)
                await self.random_delay(3, 5)
                
                # Paycom loads all jobs or has pagination, but let's just get everything visible
                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll("a")).map(a => ({
                        href: a.href,
                        text: a.innerText || a.textContent
                    }));
                }''')
                
                for link in links:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    href = link.get("href", "")
                    if not href or "/jobs/" not in href.lower():
                        continue
                        
                    text_parts = link.get("text", "").strip().split("\n")
                    if not text_parts or len(text_parts[0]) < 3:
                        continue
                        
                    title = text_parts[0].strip()
                    job_url = href if href.startswith("http") else self.base_url.rstrip("/") + "/" + href.lstrip("/")
                    
                    # Avoid duplicates
                    existing = next((j for j in jobs if j["url"] == job_url), None)
                    if existing:
                        continue
                        
                    job_id = f"flyexclusive_{abs(hash(job_url)) % 10000000}"
                    
                    jobs.append({
                        "job_id": job_id,
                        "title": title,
                        "company": self.company_name,
                        "source": self.site_key,
                        "url": job_url,
                        "apply_url": job_url,
                        "location": "Unknown",
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
                    selectors = [".job-description", "#job-details", "article", "main", ".jobDescription"]
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
                    # Backfill location from the original posting when missing.
                    if not job.get("location") or job.get("location") == "Unknown":
                        _loc = await self.extract_location_from_page(page)
                        if _loc:
                            job["location"] = _loc
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
