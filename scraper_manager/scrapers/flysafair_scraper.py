import asyncio
import logging
import re
from datetime import datetime
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class FlySafairScraper(BaseScraper):
    """Scraper for FlySafair"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="flysafair", db_manager=db_manager)
        self.site_config = config.get("sites", {}).get("flysafair", {})
        self.base_url = self.site_config.get("base_url", "https://flysafairjobs.mcidirecthire.com")
        self.jobs_url = self.site_config.get("jobs_url", "https://flysafairjobs.mcidirecthire.com/Vacancy")
        self.company_name = "FlySafair"

    async def fetch_jobs(self) -> list:
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                logger.info(f"[{self.site_key}] Loading jobs from {self.jobs_url}")
                await page.goto(self.jobs_url, wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(3000)
                
                # Cookie accept if visible
                try:
                    cookies = await page.query_selector("button:has-text('Accept'), .btn-primary:has-text('Accept'), button[onclick*='AcceptCookies']")
                    if cookies:
                        await cookies.click()
                        await page.wait_for_timeout(1000)
                except Exception as ce:
                    logger.debug(f"[{self.site_key}] Cookie banner check: {ce}")

                page_num = 1
                while True:
                    if self.max_pages and page_num > self.max_pages:
                        break
                    
                    logger.info(f"[{self.site_key}] Scraping page {page_num}...")
                    
                    # Extract jobs on current page
                    cards = await page.query_selector_all(".job-card")
                    logger.info(f"[{self.site_key}] Found {len(cards)} job cards on page {page_num}")
                    
                    # Get first card job title to check page changes
                    first_title = ""
                    if cards:
                        title_el = await cards[0].query_selector(".job-title")
                        if title_el:
                            first_title = (await title_el.inner_text()).strip()

                    for card in cards:
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break
                            
                        try:
                            # Title
                            title_el = await card.query_selector(".job-title")
                            if not title_el:
                                continue
                            title = (await title_el.inner_text()).strip()
                            
                            # Detail URL
                            share_el = await card.query_selector(".st-custom-button")
                            if not share_el:
                                continue
                            job_url = await share_el.get_attribute("data-url")
                            if not job_url:
                                continue
                            
                            # Clean details url
                            if not job_url.startswith("http"):
                                job_url = self.base_url.rstrip("/") + "/" + job_url.lstrip("/")
                            
                            # Unique job_id from parameters
                            param_match = re.search(r"parameters=([^&]+)", job_url)
                            if param_match:
                                job_id = f"flysafair_{param_match.group(1)[:32]}"
                            else:
                                job_id = f"flysafair_{abs(hash(job_url)) % 10000000}"
                                
                            # Location and Date
                            location = "Unknown"
                            posted_date = ""
                            text_muted_el = await card.query_selector(".text-muted")
                            if text_muted_el:
                                text_muted = await text_muted_el.inner_text()
                                # E.g. "2026/07/01 Cape Town"
                                date_match = re.search(r"(\d{4}/\d{2}/\d{2})", text_muted)
                                if date_match:
                                    posted_date = self.parse_posted_date(date_match.group(1))
                                    location = text_muted.replace(date_match.group(1), "").strip()
                            
                            # Department
                            department = ""
                            card_text = await card.inner_text()
                            dept_match = re.search(r"Department:\s*([^\n]+)", card_text)
                            if dept_match:
                                department = dept_match.group(1).strip()
                                
                            jobs.append({
                                "job_id": job_id,
                                "title": title,
                                "company": self.company_name,
                                "source": self.site_key,
                                "url": job_url,
                                "apply_url": job_url,
                                "location": self.normalize_location(location),
                                "posted_date": posted_date,
                                "department": department,
                                "timestamp": datetime.now().isoformat(),
                                "description": ""
                            })
                        except Exception as card_err:
                            logger.debug(f"[{self.site_key}] Error parsing card: {card_err}")
                            continue

                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    # Pagination: check next button
                    next_btn = await page.query_selector("li.page-item.next:not(.disabled) a")
                    if not next_btn:
                        logger.info(f"[{self.site_key}] No more pages (next button disabled or not found)")
                        break
                        
                    # Click next
                    logger.info(f"[{self.site_key}] Clicking next page...")
                    await next_btn.click()
                    page_num += 1
                    
                    # Wait for page update
                    page_changed = False
                    for _ in range(10):
                        await page.wait_for_timeout(500)
                        new_cards = await page.query_selector_all(".job-card")
                        if new_cards:
                            new_title_el = await new_cards[0].query_selector(".job-title")
                            if new_title_el:
                                new_title = (await new_title_el.inner_text()).strip()
                                if new_title != first_title:
                                    page_changed = True
                                    break
                    if not page_changed:
                        logger.info(f"[{self.site_key}] Page content did not change, ending pagination")
                        break
                        
            except Exception as e:
                logger.error(f"[{self.site_key}] Error during jobs fetch: {e}")
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
                    await page.wait_for_timeout(2000)
                    
                    desc_el = await page.query_selector(".job-details")
                    if desc_el:
                        desc = await desc_el.inner_text()
                        desc = re.sub(r"\s+", " ", desc).strip()
                        job["description"] = desc
                    else:
                        job["description"] = await self.extract_description_from_page(page)
                        
                    await context.close()
                except Exception as e:
                    logger.warning(f"[{self.site_key}] Failed to fetch description for {job['url']}: {e}")
            await browser.close()
            
        return jobs

    async def run(self):
        self.print_header()
        jobs_raw = await self.fetch_jobs()
        
        if not jobs_raw:
            return []
            
        if self.use_filter and self.filter_manager:
            jobs, _, _ = self.apply_title_filter(jobs_raw)
            if not jobs:
                return []
        else:
            jobs = jobs_raw
            
        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []
            
        jobs = await self.fetch_job_descriptions(jobs)
        jobs = [get_job_dict(**job) for job in jobs]
        await self.save_results(jobs)
        self.print_sample(jobs)
        return jobs
