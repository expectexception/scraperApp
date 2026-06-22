import asyncio
import logging
import re
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict
from datetime import datetime

logger = logging.getLogger(__name__)

class LarScraper(BaseScraper):
    """Scraper for LAR Careers"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="lar", db_manager=db_manager)
        self.site_config = config.get("sites", {}).get("lar", {})
        self.base_url = self.site_config.get("base_url", "https://lar.careers")
        self.jobs_url = self.site_config.get("jobs_url", "https://lar.careers/board/62729feb4cdf6e3a3a8dc30d")
        self.company_name = "LAR Careers"

    async def fetch_jobs(self) -> list:
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                logger.info(f"[{self.site_key}] Loading jobs from {self.jobs_url}")
                await page.goto(self.jobs_url, wait_until="networkidle", timeout=60000)
                await self.random_delay(3, 5)
                
                # Extract links using evaluate
                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll("a")).map(a => ({
                        href: a.href,
                        text: a.innerText || a.textContent
                    }));
                }''')
                
                for link in links:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    try:
                        href = link.get("href", "")
                        if not href: continue
                        
                        text = link.get("text", "").strip()
                        if not text or len(text) < 5: continue
                        
                        href_lower = href.lower()
                        # Generic heuristics
                        if "/job/" in href_lower or "/vacancy/" in href_lower or "/position/" in href_lower or "jobid=" in href_lower or "/view/" in href_lower or "/careers/" in href_lower or "/board/" in href_lower or "-jobs" in href_lower or "/offer/" in href_lower or "requisition" in href_lower:
                            job_url = href if href.startswith("http") else self.base_url.rstrip("/") + "/" + href.lstrip("/")
                            
                            # Skip if generic apply text
                            if text.lower() in ["read more", "apply", "apply now", "view details", "search", "search jobs", "all jobs"]:
                                continue
                                
                            # Avoid duplicates, keep the longest title
                            existing = next((j for j in jobs if j["url"] == job_url), None)
                            if existing:
                                if len(text) > len(existing["title"]):
                                    existing["title"] = text
                                continue
                                
                            job_id = f"lar_{abs(hash(job_url)) % 10000000}"
                            
                            jobs.append({
                                "job_id": job_id,
                                "title": text,
                                "company": self.company_name,
                                "source": self.site_key,
                                "url": job_url,
                                "apply_url": job_url,
                                "location": "Unknown",
                                "timestamp": datetime.now().isoformat(),
                                "description": ""
                            })
                    except:
                        continue
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
                    selectors = [".job-description", "#job-details", ".vacancy-description", ".content", "article", "main"]
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
