import asyncio
import logging
from playwright.async_api import async_playwright
import re
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class AustrianAirlinesScraper(BaseScraper):
    """
    Scraper for Austrian Airlines.
    URL: https://apply.lufthansagroup.careers/index.php?ac=search_result&search_criterion_company%5B%5D=5909&language=2
    Lufthansa Group structure.
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='austrianairlines', db_manager=db_manager)
        # Direct division filter: 5909, 5975, 5974 for Austrian Airlines
        self.base_url = "https://apply.lufthansagroup.careers/index.php?ac=search_result&search_criterion_division%5B%5D=5909&search_criterion_division%5B%5D=5975&search_criterion_division%5B%5D=5974&search_criterion_channel%5B%5D=12&language=2"
        self.company_name = "Austrian Airlines"

    async def fetch_jobs(self) -> list:
        logger.info(f"[{self.site_key}] Navigating to Lufthansa group careers portal...")
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                try:
                    # Using domcontentloaded as the site can be slow with tracking scripts
                    await page.goto(self.base_url, wait_until='domcontentloaded', timeout=60000)
                    await page.wait_for_timeout(3000)
                except Exception as e:
                    logger.error(f"[{self.site_key}] Navigation failed: {e}")
                    return []
                
                # Handling cookie consent
                try:
                    cookie_btn = page.locator('text="Select all", text="Accept all", [data-hook="cc-ccc-btn-confirm-all"], #ensAcceptAll').first
                    if await cookie_btn.is_visible():
                        await cookie_btn.click(force=True)
                        await page.wait_for_timeout(2000)
                except:
                    pass

                # Wait for results to load - results are loaded dynamically
                try:
                    # The container is 'div.jobboard-datatable'
                    # We wait for the spinner to disappear or just wait for the links
                    await page.wait_for_selector('a.jobad-link-wrapper', timeout=45000)
                except:
                    # Take screenshot if failure
                    await page.screenshot(path="austrian_failure_no_links.png")
                    logger.warning(f"[{self.site_key}] No job links found after wait. Saved screenshot.")

                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a.jobad-link-wrapper'))
                        .map(a => {
                            let h2 = a.querySelector('h2');
                            return {t: h2 ? h2.innerText.trim() : (a.title || a.innerText.trim()), h: a.href};
                        })
                        .filter(a => a.h && a.h.includes('job'))
                }''')
                
                logger.info(f"[{self.site_key}] Found {len(links)} potential job links after dynamic wait")
                
                seen_urls = set()
                initial_jobs = []
                for link in links:
                    href = link['h']
                    title = link['t']
                    if href and href not in seen_urls and self.is_job_link(title, href):
                        seen_urls.add(href)
                        initial_jobs.append({'title': title, 'url': href})
                
                logger.info(f"[{self.site_key}] Found {len(initial_jobs)} potential jobs. Applying pre-filter...")
                
                # PRE-FILTER: Filter by title first to skip irrelevant roles (like HR) completely
                matched_initial, _, _ = self.apply_title_filter(initial_jobs)
                
                logger.info(f"[{self.site_key}] {len(matched_initial)} jobs passed pre-filtering. Fetching details...")

                for i, j_initial in enumerate(matched_initial):
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    url = j_initial['url']
                    title = j_initial['title']
                    
                    try:
                        logger.info(f"[{self.site_key}] Fetching details for: {url}")
                        detail_page = await context.new_page()
                        # Increased timeout to 60s and switched to 'load' for more stability
                        await detail_page.goto(url, wait_until='load', timeout=60000)
                        await detail_page.wait_for_timeout(2000)
                        
                        real_title = title
                        h1 = detail_page.locator('h1').first
                        if await h1.is_visible():
                            extracted = await h1.inner_text()
                            if len(extracted) > 5:
                                real_title = extracted

                        description = ""
                        desc_selectors = ['.lh-jobad-content-details', '.lh-jobad-collapsible-content-todos-text', '.lh-jobad', '.jobad-content', 'main']
                        for selector in desc_selectors:
                            elem = detail_page.locator(selector).first
                            if await elem.is_visible():
                                description = await elem.inner_html()
                                break
                                
                        if not description:
                            description = await self.extract_description_from_page(detail_page)

                        location = "Austria"
                        loc_elem = detail_page.locator('.lh-jobad-content-facts li').first
                        if await loc_elem.is_visible():
                            loc_text = await loc_elem.inner_text()
                            if loc_text: location = loc_text.strip()
                        posted_date = await self.extract_posted_date_from_page(detail_page)
                        
                        job_id = f"austrian_{i+1}"
                        match = re.search(r'id=(\d+)', url)
                        if not match:
                            match = re.search(r'job/(\d+)', url)
                        if match:
                            job_id = f"austrian_{match.group(1)}"

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
