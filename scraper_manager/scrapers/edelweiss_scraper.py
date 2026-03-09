import logging
import re
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class EdelweissScraper(BaseScraper):
    """
    Scraper for Edelweiss Air.
    URL: https://www.lufthansagroup.careers/en/edelweiss
    Typically Lufthansa Group structure.
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='edelweiss', db_manager=db_manager)
        self.base_url = "https://www.lufthansagroup.careers/en/edelweiss"
        self.company_name = "Edelweiss Air"

    async def fetch_jobs(self) -> list:
        logger.info(f"[{self.site_key}] Navigating to Lufthansa group careers portal proxy...")
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                try:
                    await page.goto(self.base_url, wait_until='networkidle', timeout=60000)
                except Exception as e:
                    logger.error(f"[{self.site_key}] Navigation failed: {e}")
                    return []
                
                # Handling cookie consent
                try:
                    cookie_btn = page.locator('text=Accept all, text=Zustimmen, id=cmplz-accept-all').first
                    if await cookie_btn.is_visible():
                        await cookie_btn.click()
                        await page.wait_for_timeout(1000)
                except:
                    pass
                
                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a'))
                        .map(a => ({t: a.innerText.trim(), h: a.href}))
                        .filter(a => a.t && a.t.length > 5 && (a.h.includes('job') || a.h.includes('career') || a.h.includes('vacanc')))
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
                        logger.info(f"[{self.site_key}] Fetching details for: {url}")
                        detail_page = await context.new_page()
                        await detail_page.goto(url, wait_until='domcontentloaded', timeout=30000)
                        await detail_page.wait_for_timeout(1500)
                        
                        real_title = title
                        h1 = detail_page.locator('h1').first
                        if await h1.is_visible():
                            extracted = await h1.inner_text()
                            if len(extracted) > 5:
                                real_title = extracted

                        description = ""
                        desc_loc = detail_page.locator('.job-description, .content, main')
                        if await desc_loc.first.is_visible():
                            description = await desc_loc.first.inner_html()
                        else:
                            description = await self.extract_description_from_page(detail_page)

                        location = "Switzerland"
                        posted_date = await self.extract_posted_date_from_page(detail_page)
                        
                        job_id = f"edelweiss_{i+1}"
                        match = re.search(r'job/(\d+)', url)
                        if match:
                            job_id = f"edelweiss_{match.group(1)}"

                        job = get_job_dict(
                            job_id=job_id,
                            title=real_title,
                            company=self.company_name,
                            location=location,
                            url=url,
                            source_url=self.base_url,
                            description=description,
                            apply_url=url,
                            posted_date=posted_date,
                            source=self.site_key
                        )
                        
                        jobs.append(job)
                        await detail_page.close()
                        
                    except Exception as e:
                        logger.error(f"[{self.site_key}] Error parsing job {i} ({url}): {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
            finally:
                await context.close()
                await browser.close()
                
        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        jobs = [j for j in jobs if j is not None]
        await self.save_results(jobs)
        return jobs
