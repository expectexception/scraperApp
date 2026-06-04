import os

ICIMS_TEMPLATE = """import asyncio
import logging
import re
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class {class_name}(BaseScraper):
    \"\"\"
    Scraper for {company_name} (iCIMS)
    \"\"\"
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='{site_key}', db_manager=db_manager)
        self.base_url = "{url}"
        self.company_name = "{company_name}"

    async def fetch_jobs(self) -> list:
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                await page.goto(self.base_url, wait_until='domcontentloaded', timeout=60000)
                await page.wait_for_timeout(5000)
                
                frame = page
                iframe_el = await page.query_selector('iframe#icims_bootstrap_frame, iframe')
                if iframe_el:
                    frame = page.frame_locator('iframe#icims_bootstrap_frame').first
                    if not await frame.locator('.iCIMS_JobsTable').is_visible(timeout=5000):
                        frame = page.frame_locator('iframe').first

                job_rows = await frame.locator('.iCIMS_JobsTable .row, .iCIMS_JobListing').all()
                for row in job_rows:
                    if self.max_jobs and len(jobs) >= self.max_jobs: break
                    try:
                        title_el = row.locator('div.title a.iCIMS_Anchor, a.iCIMS_JobListingLink').first
                        if not await title_el.is_visible(): continue
                        title = await title_el.inner_text()
                        url = await title_el.get_attribute('href')
                        if url and '?' in url: url = url.split('?')[0]
                        if url and not url.startswith('http'): url = "https://" + "{url}".split('/')[2] + url
                        
                        location = "USA"
                        loc_el = row.locator('.header.left span:not(.sr-only), .location span:nth-child(2)').first
                        if await loc_el.is_visible(): location = await loc_el.inner_text()
                        
                        job_id = f"{site_key}_" + str(hash(url))
                        
                        jobs.append({{
                            'company': self.company_name,
                            'title': title.strip(),
                            'location': location.strip(),
                            'url': url,
                            'apply_url': url,
                            'source_url': self.base_url,
                            'job_id': job_id,
                            'description': ''
                        }})
                    except:
                        pass
            except Exception as e:
                logger.error(f"[{{self.site_key}}] Error: {{e}}")
            finally:
                await context.close()
                await browser.close()
                
        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        if self.use_filter and self.filter_manager and jobs:
            jobs, _, _ = self.apply_title_filter(jobs)
        await self.save_results(jobs)
        return jobs
"""

WORKDAY_TEMPLATE = """import asyncio
import logging
import requests
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class {class_name}(BaseScraper):
    \"\"\"
    Scraper for {company_name} (Workday/Custom API)
    \"\"\"
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='{site_key}', db_manager=db_manager)
        self.base_url = "{url}"
        self.company_name = "{company_name}"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{{self.site_key}}] Workday/API scraper starting...")
        # Stub implementation
        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        if self.use_filter and self.filter_manager and jobs:
            jobs, _, _ = self.apply_title_filter(jobs)
        await self.save_results(jobs)
        return jobs
"""

scrapers = [
    {"site_key": "alaska", "class_name": "AlaskaScraper", "company_name": "Alaska Airlines", "url": "https://careers.alaskaair.com/jobs/search?in_iframe=1", "template": ICIMS_TEMPLATE},
    {"site_key": "skywest", "class_name": "SkyWestScraper", "company_name": "SkyWest Airlines", "url": "https://skywest-airlines.icims.com/jobs/search?in_iframe=1", "template": ICIMS_TEMPLATE},
    {"site_key": "republic", "class_name": "RepublicScraper", "company_name": "Republic Airways", "url": "https://rjet.com/careers", "template": ICIMS_TEMPLATE},
    {"site_key": "endeavor", "class_name": "EndeavorScraper", "company_name": "Endeavor Air", "url": "https://www.endeavorair.com/careers", "template": ICIMS_TEMPLATE},
    {"site_key": "frontier", "class_name": "FrontierScraper", "company_name": "Frontier Airlines", "url": "https://www.flyfrontier.com/careers", "template": WORKDAY_TEMPLATE},
    {"site_key": "dhl", "class_name": "DHLScraper", "company_name": "DHL Aviation", "url": "https://careers.dhl.com", "template": WORKDAY_TEMPLATE},
]

import sys
base_dir = "/home/rajat/Desktop/AeroOps Intel/scraper-standalone"

for s in scrapers:
    file_path = os.path.join(base_dir, "scraper_manager/scrapers", f"{s['site_key']}_scraper.py")
    with open(file_path, "w") as f:
        f.write(s['template'].format(**s))

print("Created scraper files")

