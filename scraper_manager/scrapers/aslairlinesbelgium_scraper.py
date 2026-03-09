import asyncio
import logging
from datetime import datetime
from playwright.async_api import async_playwright
import re

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class ASLAirlinesBelgiumScraper(BaseScraper):
    """
    Scraper for ASL Airlines Belgium
    URL: https://aslairlines.be/asljobs/
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='aslairlinesbelgium', db_manager=db_manager)
        self.base_url = "https://aslairlines.be/asljobs/"
        self.company_name = "ASL Airlines Belgium"

    async def fetch_jobs(self) -> list:
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                
                try:
                    await page.goto(self.base_url, wait_until='networkidle', timeout=60000)
                except Exception as e:
                    logger.error(f"[{self.site_key}] Navigation failed: {e}")
                    return []
                
                # Links to jobs are usually /job/ or within the domain
                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a'))
                        .map(a => ({t: a.innerText.trim(), h: a.href}))
                        .filter(a => a.t && a.t.length > 3 && a.h.includes('aslairlines.be') && !a.h.includes('contact') && !a.h.includes('about'))
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
                        
                        await detail_page.wait_for_timeout(2000)
                            
                        description = ""
                        desc_loc = detail_page.locator('main, .elementor-widget-container, .entry-content, article')
                        if await desc_loc.first.is_visible():
                            description = await desc_loc.first.inner_html()
                                
                        if not description:
                            description = await self.extract_description_from_page(detail_page)

                        location = "Liege/Belgium" # ASL Airlines Belgium hub
                        
                        posted_date = await self.extract_posted_date_from_page(detail_page)

                        job_id = url.strip('/').split('/')[-1]

                        job = get_job_dict(
                            job_id=f"aslbe_{job_id}",
                            title=title,
                            company=self.company_name,
                            location=location,
                            url=url,
                            source_url=url,
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
