import asyncio
import logging
import re
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class JetstarScraper(BaseScraper):
    """
    Scraper for Jetstar
    URL: https://careers.jetstar.com/jobs/
    """
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="jetstar", db_manager=db_manager)
        self.base_url = "https://careers.jetstar.com/jobs/"
        self.company_name = "Jetstar"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        async with async_playwright() as p:
            # Must run headful to avoid HTTP2 protocol error / Akamai blocks
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
                
                page_count = 1
                while True:
                    if self.max_pages and page_count > self.max_pages:
                        break
                        
                    logger.info(f"[{self.site_key}] Processing page {page_count}...")
                    try:
                        await page.wait_for_selector(".afp-job-card", timeout=15000)
                    except Exception as e:
                        logger.warning(f"[{self.site_key}] No jobs found or timeout: {e}")
                        break

                    cards = await page.query_selector_all(".afp-job-card")
                    logger.info(f"[{self.site_key}] Found {len(cards)} job cards on page {page_count}.")
                    
                    page_jobs = []
                    for card in cards:
                        try:
                            title_el = await card.query_selector(".afp-job-title")
                            if not title_el:
                                continue
                            title = await title_el.inner_text()
                            title = title.strip()
                            
                            link_el = await card.query_selector(".afp-btn-view-job")
                            if not link_el:
                                continue
                            href = await link_el.get_attribute("href")
                            if not href:
                                continue
                                
                            job_url = href if href.startswith("http") else f"https://careers.jetstar.com{href}"
                            
                            # Location
                            loc_el = await card.query_selector(".afp-job-location")
                            location = await loc_el.inner_text() if loc_el else "Australia"
                            location = location.strip().replace("\n", " ")
                            
                            # Posted date text
                            posted_el = await card.query_selector(".afp-job-posted")
                            posted_text = await posted_el.inner_text() if posted_el else ""
                            posted_date = self.parse_posted_date(posted_text) if posted_text else None
                            
                            # Summary/description
                            desc_el = await card.query_selector(".afp-job-card-v2-summary")
                            description = await desc_el.inner_text() if desc_el else ""
                            
                            page_jobs.append({
                                "title": title,
                                "url": job_url,
                                "location": location,
                                "posted_date": posted_date,
                                "description": description.strip(),
                            })
                        except Exception as e:
                            logger.error(f"[{self.site_key}] Error parsing card: {e}")
                            continue

                    for job_data in page_jobs:
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break
                            
                        url = job_data["url"]
                        title = job_data["title"]
                        
                        if not self.is_job_link(title, url):
                            continue
                        if not self.should_process_job(title):
                            continue
                        if await self.is_url_already_scraped(url):
                            continue
                            
                        job_id_match = re.search(r"/job-details/(\d+)/", url)
                        job_id = f"jetstar_{job_id_match.group(1)}" if job_id_match else f"jetstar_{abs(hash(url)) % 10000000}"
                        
                        jobs.append(get_job_dict(
                            job_id=job_id,
                            title=title,
                            company=self.company_name,
                            location=job_data["location"],
                            url=url,
                            source_url=self.base_url,
                            description=job_data["description"],
                            apply_url=url,
                            posted_date=job_data["posted_date"],
                            source=self.site_key,
                        ))

                    # Pagination: click Next button
                    try:
                        next_btn = page.locator(".afp-pagination-item page-item:not(.disabled) a[aria-label='Go to next page']").first
                        # Alternate selector for robustness
                        if not await next_btn.is_visible():
                            next_btn = page.locator("a:has-text('Next')").first
                            
                        if await next_btn.is_visible() and await next_btn.is_enabled():
                            logger.info(f"[{self.site_key}] Clicking Next page...")
                            await next_btn.click()
                            await page.wait_for_timeout(5000)
                            page_count += 1
                        else:
                            logger.info(f"[{self.site_key}] Next button not clickable or visible.")
                            break
                    except Exception as e:
                        logger.info(f"[{self.site_key}] Pagination ended or error: {e}")
                        break
            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
            finally:
                await context.close()
                await browser.close()
        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        if not jobs: return []
        if self.use_filter and self.filter_manager:
            jobs, _, _ = self.apply_title_filter(jobs)
            if not jobs: return []
        jobs, _ = await self.filter_new_jobs(jobs)
        await self.save_results(jobs)
        return jobs
