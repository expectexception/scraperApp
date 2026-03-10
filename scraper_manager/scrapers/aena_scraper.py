import asyncio
import logging
from datetime import datetime
from playwright.async_api import async_playwright
import re

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class AenaScraper(BaseScraper):
    """
    Scraper for Aena Empleo (Spain)
    URL: https://empleo.aena.es/empleo/PFSrv?accion=inicio&SEDE=0
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='aena', db_manager=db_manager)
        self.base_url = "https://empleo.aena.es/empleo/PFSrv?accion=inicio&SEDE=0"
        self.company_name = "Aena"

    async def fetch_jobs(self) -> list:
        jobs = []
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080}
                )
                page = await context.new_page()
                
                logger.info(f"[{self.site_key}] Loading Aena careers page...")
                await page.goto(self.base_url, wait_until='networkidle', timeout=45000)
                
                job_headers = await page.locator('div.th').all()
                logger.info(f"[{self.site_key}] Found {len(job_headers)} potential job rows")
                
                for i, header in enumerate(job_headers):
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    title_elem = header.locator('h3').first
                    if not await title_elem.is_visible():
                        continue
                    title = await title_elem.inner_text()
                    
                    # Look for the immediate next sibling div.td3 containing a.botonAvisos
                    link_elem = header.locator('xpath=following-sibling::div[contains(@class, "td3")][1]//a[contains(@class, "botonAvisos")]').first
                    if await link_elem.is_visible():
                        href = await link_elem.get_attribute('href')
                        full_url = f"https://empleo.aena.es/empleo/{href}" if 'http' not in href else href
                        
                        match = re.search(r'idProceso=(\d+)', href)
                        jid = match.group(1) if match else f"{i}"
                        
                        job = get_job_dict(
                            job_id=f"aena_{jid}",
                            title=title.strip(),
                            company=self.company_name,
                            location="Spain",
                            url=full_url,
                            source_url=self.base_url,
                            description=f"Aena recruitment process: {title.strip()}. See documents at the provided URL.",
                            apply_url=full_url,
                            posted_date=datetime.now().isoformat(),
                            source=self.site_key
                        )
                        jobs.append(job)
                        
                await browser.close()
        except Exception as e:
            logger.error(f"[{self.site_key}] Error: {e}")
            
        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        jobs = [j for j in jobs if j is not None]
        await self.save_results(jobs)
        return jobs
