import asyncio
import logging
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class AlsieExpressScraper(BaseScraper):
    """
    Scraper for Alsie Express.
    Currently, they do not have an active ATS or published careers section, 
    only a spontaneous contact page. Safely returns empty.
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='alsieexpress', db_manager=db_manager)
        self.base_url = "https://air-alsie.career.emply.com/en"
        self.company_name = "Alsie Express"

    async def fetch_jobs(self) -> list:
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until='networkidle', timeout=60000)
                # Look for job links in the Air Alsie portal
                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a'))
                        .filter(a => a.href.includes('/en/ad/'))
                        .map(a => ({t: a.innerText.trim(), h: a.href}))
                }''')
                for l in links:
                    if self.is_job_link(l['t'], l['h']):
                        job_id = l['h'].split('/')[-1]
                        jobs.append(get_job_dict(
                            job_id=f"alsie_{job_id}",
                            title=l['t'],
                            company=self.company_name,
                            location="Denmark",
                            url=l['h'],
                            source=self.site_key
                        ))
            except Exception as e:
                logger.error(f"[{self.site_key}] Error: {e}")
            finally:
                await browser.close()
        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        await self.save_results(jobs)
        return jobs
