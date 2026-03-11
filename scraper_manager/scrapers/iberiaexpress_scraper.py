import asyncio
import logging
import re
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class IberiaExpressScraper(BaseScraper):
    """
    Scraper for Iberia Express.
    Uses Playwright with headful mode support for WAF bypass.
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='iberiaexpress', db_manager=db_manager)
        self.base_url = "https://career2.successfactors.eu/career?company=iberia"
        self.company_name = "Iberia Express"

    async def fetch_jobs(self) -> list:
        logger.info(f"[{self.site_key}] Navigating to {self.base_url} (Headless={self.headless})...")
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                # Custom portal might need extra time
                await page.goto(self.base_url, wait_until='networkidle', timeout=60000)
                await self.simulate_human_behavior(page)
                
                # Use standard SuccessFactors selector
                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a.jobTitle-link'))
                        .map(a => ({t: (a.innerText || '').trim(), h: a.href}))
                        .filter(a => a.h)
                }''')
                
                logger.info(f"[{self.site_key}] Found {len(links)} potential job links")
                
                seen_urls = set()
                job_urls = []
                for link in links:
                    href = link['h']
                    title = link['t']
                    if href and href not in seen_urls and self.is_job_link(title, href):
                        seen_urls.add(href)
                        job_urls.append((href, title))
                
                for i, (url, title) in enumerate(job_urls):
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                    
                    try:
                        if not self.should_process_job(title):
                            continue

                        if await self.is_url_already_scraped(url):
                            continue

                        logger.info(f"[{self.site_key}] Fetching details for: {url}")
                        detail_page = await context.new_page()
                        await detail_page.goto(url, wait_until='domcontentloaded', timeout=30000)
                        await self.random_delay(1, 2)
                        
                        description = await self.extract_description_from_page(detail_page)
                        
                        job_id = f"{self.site_key}_{re.sub(r'[^a-zA-Z0-9]', '', url)[-10:]}"
                        
                        job = get_job_dict(
                            job_id=job_id,
                            title=title,
                            company=self.company_name,
                            location="Various",
                            url=url,
                            source_url=self.base_url,
                            description=description,
                            source=self.site_key
                        )
                        jobs.append(job)
                        await detail_page.close()
                    except Exception as e:
                        logger.warning(f"[{self.site_key}] Error detail page {url}: {e}")
                        
            except Exception as e:
                logger.error(f"[{self.site_key}] Main page error: {e}")
            finally:
                await context.close()
                await browser.close()
                
        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        
        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
