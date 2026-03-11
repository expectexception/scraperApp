import asyncio
import logging
import re
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class TransaviaScraper(BaseScraper):
    """
    Scraper for Transavia.
    Uses Playwright with headful mode support for WAF bypass.
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='transavia', db_manager=db_manager)
        self.base_url = "https://werkenbijtransavia.com/l/en/vacatures"
        self.company_name = "Transavia"

    async def fetch_jobs(self) -> list:
        logger.info(f"[{self.site_key}] Navigating to {self.base_url} (Headless={self.headless})...")
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                page.on("response", lambda response: asyncio.create_task(self.log_api_response(response)))
                await page.goto(self.base_url, wait_until='networkidle', timeout=60000)
                await page.screenshot(path='transavia_debug.png')
                
                # Try accepting cookies
                try:
                    cookie_btn = await page.query_selector('button:has-text("Agree"), button:has-text("Akkoord")')
                    if cookie_btn:
                        await cookie_btn.click()
                        await page.wait_for_timeout(2000)
                except Exception:
                    pass
                
                # Scroll down to load all jobs
                for _ in range(3):
                    await page.evaluate('window.scrollBy(0, 1000)')
                    await page.wait_for_timeout(1000)
                
                await self.simulate_human_behavior(page)
                await page.wait_for_timeout(2000)
                
                # Check for 'No results' message specifically in the grid area or main
                content = await page.content()
                if "No open positions matching selected filters" in content:
                    logger.info(f"[{self.site_key}] No jobs found matching filters.")
                    return []

                # Look for vacancy links - specifically targetting '/o/'
                # Using [data-testid="offer-list-grid"] to focus on actual job cards
                links = await page.evaluate('''() => {
                    const grid = document.querySelector('[data-testid="offer-list-grid"]') || document.querySelector('main') || document.body;
                    return Array.from(grid.querySelectorAll('a'))
                        .map(a => ({t: (a.innerText || '').trim(), h: a.href}))
                        .filter(a => {
                            if (!a.h || !a.h.includes('/o/')) return false;
                            // Skip language variants and common junk
                            if (a.h.includes('?lang=') || a.h.includes('jobalert') || a.h.includes('whatsapp')) return false;
                            return true;
                        })
                }''')
                
                logger.info(f"[{self.site_key}] Found {len(links)} unique job links in grid")
                
                seen_urls = set()
                job_urls = []
                for link in links:
                    href = link['h']
                    title = link['t']
                    logger.info(f"[{self.site_key}] Checking link: {title} | {href}")
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

    async def log_api_response(self, response):
        """Log API responses to find the hidden endpoint"""
        try:
            if "json" in response.headers.get("content-type", "") or "graphql" in response.url:
                logger.info(f"[transavia-api] Captured endpoint: {response.url}")
        except Exception:
            pass

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        
        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
