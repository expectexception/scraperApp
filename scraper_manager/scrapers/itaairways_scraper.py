import asyncio
import logging
import re
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class ITAScraper(BaseScraper):
    """
    Scraper for ITA Airways.
    Uses Playwright with headful mode support for WAF bypass.
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='itaairways', db_manager=db_manager)
        self.base_url = "https://career.ita-airways.com/search/"
        self.company_name = "ITA Airways"

    async def fetch_jobs(self) -> list:
        logger.info(f"[{self.site_key}] Navigating to {self.base_url} (Headless={self.headless})...")
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                # Direct navigation to search results
                await page.goto(self.base_url, wait_until='networkidle', timeout=60000)
                # Wait for job listings to load
                await page.wait_for_selector('a.jobCardTitle', timeout=30000)
                await self.simulate_human_behavior(page)
                
                # Extract job links using the correct selector
                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a.jobCardTitle'))
                        .map(a => ({t: (a.innerText || '').trim(), h: a.getAttribute('href')}))
                        .filter(a => a.h)
                }''')
                
                logger.info(f"[{self.site_key}] Found {len(links)} potential job links")
                
                seen_urls = set()
                initial_jobs = []
                base_site_url = "https://career.ita-airways.com"
                
                for link in links:
                    href = link['h']
                    # Convert relative URL to absolute
                    if href.startswith('/'):
                        href = base_site_url + href
                    elif not href.startswith('http'):
                        href = base_site_url + '/' + href
                        
                    title = link['t']
                    if href and href not in seen_urls and title:
                        seen_urls.add(href)
                        initial_jobs.append({'title': title, 'url': href})
                
                logger.info(f"[{self.site_key}] {len(initial_jobs)} potential jobs. Applying pre-filter...")
                
                # PRE-FILTER: Filter by title first to skip irrelevant roles COMPLETELY
                matched_initial, _, _ = self.apply_title_filter(initial_jobs)
                
                logger.info(f"[{self.site_key}] {len(matched_initial)} jobs passed pre-filtering. Fetching details...")

                for i, j_initial in enumerate(matched_initial):
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                    
                    url = j_initial['url']
                    title = j_initial['title']
                    
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
                        
                        job_id = f"ita_{re.sub(r'[^a-zA-Z0-9]', '', url)[-10:]}"
                        
                        job = get_job_dict(
                            job_id=job_id,
                            title=title,
                            company=self.company_name,
                            location="Italy",
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
