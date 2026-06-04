import asyncio
import logging
from typing import List, Dict
from .base_scraper import BaseScraper
from .job_schema import get_job_dict
from playwright.async_api import async_playwright
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class AmentumScraper(BaseScraper):
    """Scraper for Amentum careers via Playwright."""

    def __init__(self, config: Dict, db_manager=None):
        super().__init__(config, site_key="amentum", db_manager=db_manager)
        self.base_url = "https://www.amentumcareers.com/jobs/search?query="
        self.company_name = "Amentum"

    async def fetch_jobs(self) -> List[Dict]:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
                
                job_data_list = []
                
                while True:
                    await page.wait_for_timeout(2000)
                    
                    try:
                        await page.wait_for_selector('td.job-search-results-title', timeout=15000)
                    except Exception as e:
                        logger.warning(f"[{self.site_key}] Timeout waiting for job list: {e}")
                        break

                    job_rows = await page.query_selector_all('tr:has(td.job-search-results-title)')
                    
                    if not job_rows:
                        break
                        
                    logger.info(f"[{self.site_key}] Found {len(job_rows)} job elements on current page.")

                    for row in job_rows:
                        title_el = await row.query_selector('td.job-search-results-title a')
                        if not title_el:
                            continue

                        title = (await title_el.inner_text()).strip()
                        href = await title_el.get_attribute("href")
                        if not href:
                            continue

                        job_url = urljoin(self.base_url, href)

                        location = "Unknown"
                        loc_el = await row.query_selector('td.job-search-results-location')
                        if loc_el:
                            location = (await loc_el.inner_text()).strip()

                        if not self.should_process_job(title):
                            continue

                        if await self.is_url_already_scraped(job_url):
                            continue

                        job_data_list.append({
                            "title": title, 
                            "url": job_url, 
                            "location": location
                        })

                        if self.max_jobs and len(job_data_list) >= self.max_jobs:
                            break
                            
                    if self.max_jobs and len(job_data_list) >= self.max_jobs:
                        break
                        
                    next_btn = await page.query_selector('li.next_page a, a[rel="next"]')
                    if next_btn:
                        is_disabled = await next_btn.evaluate('el => el.parentElement.classList.contains("disabled")')
                        if not is_disabled:
                            next_href = await next_btn.get_attribute("href")
                            if next_href:
                                next_url = urljoin(self.base_url, next_href)
                                logger.info(f"[{self.site_key}] Navigating to next page: {next_url}")
                                await page.goto(next_url, wait_until="domcontentloaded", timeout=60000)
                            else:
                                break
                        else:
                            break
                    else:
                        break
                for item in job_data_list:
                    logger.info(f"[{self.site_key}] Fetching details for: {item['title']}...")
                    await page.goto(item["url"], wait_until="domcontentloaded", timeout=60000)
                    
                    try:
                        await page.wait_for_selector('.job-description, .description, #job-description', timeout=15000)
                        desc_el = await page.query_selector('.job-description, .description, #job-description')
                        description = await desc_el.inner_html() if desc_el else "Description not found."
                    except:
                        description = "Description timeout or not found."

                    job = get_job_dict(
                        job_id=f"{self.site_key}_{hash(item["url"])}",
                        title=item["title"],
                        company=self.company_name,
                        location=item["location"],
                        url=item["url"],
                        source_url=self.base_url if hasattr(self, 'base_url') else item["url"],
                        description=description,
                        apply_url=item["url"],
                        source=self.site_key
                    )
                    jobs.append(job)

                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                return jobs

            except Exception as e:
                logger.error(f"[{self.site_key}] Scraper failed: {e}")
                return jobs
            finally:
                await browser.close()

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        matched_jobs, rejected_jobs, stats = self.apply_title_filter(jobs)
        await self.save_results(matched_jobs)
        return matched_jobs
