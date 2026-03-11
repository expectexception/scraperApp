import asyncio
import logging
import re
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class EgyptairScraper(BaseScraper):
    """
    Scraper for Egyptair.
    Uses Playwright with headful mode support for WAF bypass.
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='egyptair', db_manager=db_manager)
        self.base_url = "https://www.egyptair.com/en/about-egyptair/Pages/careers.aspx"
        self.company_name = "Egyptair"

    async def fetch_jobs(self) -> list:
        logger.info(f"[{self.site_key}] Navigating to {self.base_url} (Headless={self.headless})...")
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                await page.goto(self.base_url, wait_until='domcontentloaded', timeout=60000)
                await self.simulate_human_behavior(page)
                
                # Cloudflare Turnstile Bypass
                try:
                    cf_frame = page.frame_locator('iframe[title*="widget containing a Cloudflare security challenge"]').first
                    checkbox = cf_frame.locator('input[type="checkbox"]')
                    await checkbox.wait_for(state='visible', timeout=10000)
                    logger.info(f"[{self.site_key}] Hovering over Cloudflare Turnstile checkbox...")
                    await checkbox.hover()
                    await page.wait_for_timeout(500)
                    logger.info(f"[{self.site_key}] Clicking Cloudflare Turnstile checkbox...")
                    box = await checkbox.bounding_box()
                    if box:
                        await page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                    else:
                        await checkbox.click()
                    await page.wait_for_timeout(8000)
                except Exception as e:
                    logger.debug(f"[{self.site_key}] Cloudflare challenge not found or already verified: {e}")
                    await page.screenshot(path='egyptair_debug.png')
                
                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a'))
                        .map(a => ({t: (a.innerText || '').trim(), h: a.href}))
                        .filter(a => a.h && (a.h.includes('job') || a.h.includes('vacancy') || a.h.includes('career')))
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

    async def setup_stealth_page(self, browser):
        """Create a stealthy page context to bypass Cloudflare Turnstile"""
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: 'denied' }) : originalQuery(parameters)
            );
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        """)

        page = await context.new_page()

        try:
            cdp = await context.new_cdp_session(page)
            await cdp.send("Network.setUserAgentOverride", {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                "platform": "Win32",
                "acceptLanguage": "en-US,en;q=0.9",
            })
        except Exception as e:
            logger.warning(f"CDP Stealth Error: {e}")

        return page, context
