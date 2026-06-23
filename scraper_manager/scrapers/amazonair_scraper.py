import itertools
import logging
import re
from datetime import datetime
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class AmazonAirScraper(BaseScraper):
    """Scraper for Amazon Air Jobs"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="amazon_air", db_manager=db_manager)
        self.site_config = config.get("sites", {}).get("amazon_air", {})
        self.base_url = "https://amazon.jobs"
        self.jobs_url = "https://amazon.jobs/content/en/teams/transportation-shipping-logistics/air#jobs-search"
        self.company_name = "Amazon Air"

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
                    await page.wait_for_selector('a[href*="/jobs/"]', timeout=30000)
                except Exception:
                    logger.warning(f"[{self.site_key}] Timeout waiting for job links")
                
                await self.random_delay(3, 5)
                
                # Keep clicking "load more" until the button is gone (no artificial cap)
                for click_count in itertools.count(1):
                    if self.max_pages and click_count > self.max_pages:
                        break
                    try:
                        load_more = await page.query_selector("button.load-more-btn")
                        if load_more and await load_more.is_visible():
                            await load_more.click()
                            await self.random_delay(2, 4)
                        else:
                            break
                    except Exception:
                        break
                
                cards_data = await page.evaluate('''() => {
                    let cardElements = Array.from(document.querySelectorAll("div[class*='job-card-module_root']"));
                    return cardElements.map(card => {
                        let anchor = card.querySelector("a[href*='/jobs/']");
                        if (!anchor) return null;
                        let lines = card.innerText.split('\\n').map(l => l.trim()).filter(l => l);
                        return {
                            href: anchor.href,
                            title: lines[0] || anchor.innerText.trim(),
                            location: lines[1] || "Unknown"
                        };
                    }).filter(c => c !== null);
                }''')
                
                seen = set()
                for c in cards_data:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    job_url = c["href"]
                    if job_url in seen:
                        continue
                    seen.add(job_url)
                    
                    title = c["title"]
                    location = c["location"]
                    
                    # Normalize location
                    location = self.normalize_location(location)
                    
                    job_id = f"amazonair_{abs(hash(job_url)) % 10000000}"
                    
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
                    selectors = [".job-description", ".description", "#job-detail-body", "article", "main"]
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
            print("\n🔍 Applying title filter...")
            matched_jobs, rejected_jobs, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)
            if not matched_jobs:
                print("❌ No jobs matched the filter criteria")
                return []
            jobs = matched_jobs
                
        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []
            
        jobs = await self.fetch_job_descriptions(jobs)
        await self.save_results(jobs)
        return jobs
