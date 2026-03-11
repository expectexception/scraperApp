import asyncio
import logging
from datetime import datetime
from playwright.async_api import async_playwright
import re

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class EasyJetScraper(BaseScraper):
    """
    Scraper for easyJet
    URL: https://careers.easyjet.com/en
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='easyjet', db_manager=db_manager)
        self.base_url = "https://careers.easyjet.com/en"
        self.company_name = "easyJet"

    async def fetch_jobs(self) -> list:
        jobs = []
        apply_now_url = "https://careers.easyjet.com/en/apply-now"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                base_taleo_url = "https://easyjet.taleo.net/careersection/2/jobsearch.ftl"
                logger.info(f"[{self.site_key}] Navigating to {base_taleo_url}...")
                await page.goto(base_taleo_url, wait_until='domcontentloaded', timeout=60000)
                await page.wait_for_timeout(3000)
                
                # Click 'View All Jobs'
                try:
                    clear_btn = page.locator('#clearButton').first
                    if await clear_btn.is_visible():
                        await clear_btn.click()
                        await page.wait_for_timeout(3000)
                except Exception as e:
                    logger.warning(f"[{self.site_key}] Could not click clearButton: {e}")
                
                # Wait for job list
                try:
                    await page.wait_for_selector('a[href*="jobdetail.ftl"]', timeout=15000)
                except:
                    logger.error(f"[{self.site_key}] No jobs loaded on Taleo portal.")
                    return []

                # Extract job links
                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a[href*="jobdetail.ftl"]'))
                        .map(a => ({t: a.innerText.trim(), h: a.href}))
                        .filter(a => a.t && a.t.length > 3)
                }''')
                
                logger.info(f"[{self.site_key}] Found {len(links)} job links")
                
                seen_job_urls = set()
                for link in links:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    url = link['h']
                    title = link['t']
                    
                    if url in seen_job_urls:
                        continue
                    seen_job_urls.add(url)
                    
                    if not self.is_job_link(title, url):
                        continue

                    try:
                        if not self.should_process_job(title):
                            continue

                        if await self.is_url_already_scraped(url):
                            continue

                        logger.info(f"[{self.site_key}] Fetching details for: {url}")
                        detail_page = await context.new_page()
                        await detail_page.goto(url, wait_until='domcontentloaded', timeout=30000)
                        await detail_page.wait_for_timeout(2000)
                        
                        real_title = title
                        h1 = detail_page.locator('h1').first
                        if await h1.is_visible():
                            extracted = await h1.inner_text()
                            if len(extracted) > 5:
                                real_title = extracted

                        description = await self.extract_description_from_page(detail_page)
                        location = "Europe"
                        
                        loc_text = await detail_page.evaluate('''() => {
                            let fields = Array.from(document.querySelectorAll('.editableschematicfield label'));
                            for(let f of fields) {
                                if(f.innerText.includes('Location')) {
                                    return f.nextElementSibling ? f.nextElementSibling.innerText.trim() : "";
                                }
                            }
                            return "";
                        }''')
                        if loc_text:
                            location = loc_text

                        posted_date = await self.extract_posted_date_from_page(detail_page)
                        
                        job_id = f"easyjet_{hash(url)}"
                        match = re.search(r'job=([^&]+)', url)
                        if match:
                            job_id = f"easyjet_{match.group(1)}"

                        job = get_job_dict(
                            job_id=job_id,
                            title=real_title,
                            company=self.company_name,
                            location=location,
                            url=url,
                            source_url=base_taleo_url,
                            description=description,
                            apply_url=url,
                            posted_date=posted_date,
                            source=self.site_key
                        )
                        
                        jobs.append(job)
                        await detail_page.close()
                        
                    except Exception as e:
                        logger.error(f"[{self.site_key}] Error parsing job detail ({url}): {e}")
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
        
        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
