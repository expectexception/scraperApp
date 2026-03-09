import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class SouthwestScraper(BaseScraper):
    """
    Scraper for Southwest Airlines Careers
    URL: https://careers.southwestair.com/us/en/search-results
    Platform: Phenom People
    """
    
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key='southwest', db_manager=db_manager)
        self.base_url = "https://careers.southwestair.com/us/en/search-results"
        self.company_name = "Southwest Airlines"
        
    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Scrape jobs from Southwest careers page
        """
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            try:
                page = await context.new_page()
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                
                try:
                    await page.goto(self.base_url, wait_until='domcontentloaded', timeout=60000)
                    await page.wait_for_timeout(5000) # Wait for Phenom app to init
                    
                    # Try to close chatbot if it exists (generic Phenom selector)
                    try:
                        await page.locator('.phenom-bot-close').click(timeout=2000)
                    except:
                        pass
                        
                    # Wait for job list
                    await page.wait_for_selector('li.jobs-list-item', timeout=20000)
                    
                except Exception as e:
                    logger.error(f"[{self.site_key}] Navigation/Loading failed: {e}")
                    return []
                
                while True:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    # Get visible jobs
                    job_items = await page.locator('li.jobs-list-item').all()
                    logger.info(f"[{self.site_key}] Found {len(job_items)} jobs on current page")
                    
                    for item in job_items:
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break
                            
                        try:
                            # Use data attributes for reliability where possible
                            title_el = item.locator('[data-ph-at-id="job-title-text"]')
                            if not await title_el.count():
                                # Fallback to class
                                title_el = item.locator('.job-title')
                                
                            if not await title_el.count():
                                continue
                                
                            title = await title_el.text_content()
                            title = title.strip()
                            
                            # Location
                            loc_el = item.locator('[data-ph-at-id="job-location-text"]')
                            if not await loc_el.count():
                                loc_el = item.locator('.job-location')
                            
                            location = await loc_el.text_content() if await loc_el.count() else "Unknown Location"
                            location = location.strip().replace('\n', ' ').strip()
                            
                            # Link
                            link_el = item.locator('a[data-ph-at-id="job-link"]')
                            if not await link_el.count():
                                continue
                                
                            link = await link_el.get_attribute('href')
                            if not link:
                                continue
                                
                            # Ensure full URL
                            if not link.startswith('http'):
                                link = f"https://careers.southwestair.com{link}" if link.startswith('/') else f"https://careers.southwestair.com/us/en/{link}"
                                
                            job = {
                                'company': self.company_name,
                                'title': title,
                                'location': location,
                                'url': link,
                                'source_url': link,
                                'apply_url': link,
                                'is_active': True,
                                'description': ''
                            }
                            
                            jobs.append(job)
                            
                        except Exception as e:
                            logger.warning(f"[{self.site_key}] Error parsing job item: {e}")
                            continue

                    # Pagination Logic
                    # Look for Next button
                    next_btn = page.locator('a[data-ph-at-id="pagination-next"]')
                    
                    if await next_btn.is_visible() and await next_btn.is_enabled():
                        # Check if it has 'disabled' class or similar
                        classes = await next_btn.get_attribute('class') or ''
                        if 'disabled' in classes.lower():
                            logger.info(f"[{self.site_key}] Next button disabled. Reached end.")
                            break
                            
                        logger.info(f"[{self.site_key}] Navigating to next page...")
                        await next_btn.click()
                        await page.wait_for_timeout(3000) # Wait for page transition
                        await page.wait_for_selector('li.jobs-list-item', timeout=10000)
                    else:
                        logger.info(f"[{self.site_key}] No next button found. Reached end.")
                        break

                # Detail Extraction
                logger.info(f"[{self.site_key}] Extracting details for {len(jobs)} jobs...")
                for job in jobs:
                    if not job['url']:
                        continue
                        
                    try:
                        # Open new page for details
                        detail_page = await context.new_page()
                        await detail_page.goto(job['url'], wait_until='domcontentloaded', timeout=30000)
                        
                        # Description
                        desc_el = detail_page.locator('.job-description')
                        if await desc_el.count():
                            job['description'] = await desc_el.inner_html()
                        else:
                            # Fallback
                            job['description'] = await detail_page.content()
                            
                        # Apply Link
                        # Usually "Apply Now" button
                        apply_btn = detail_page.locator('a.primary-button') # As seen in analysis
                        # Or data-ph-at-id="apply-link" or similar
                        
                        if await apply_btn.count():
                             href = await apply_btn.first.get_attribute('href')
                             if href:
                                 job['apply_url'] = href if href.startswith('http') else f"https://careers.southwestair.com{href}"
                        
                        await detail_page.close()
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        logger.warning(f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}")
                        
            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
            finally:
                await browser.close()
                
        return jobs

    async def run(self):
        """Main entry point for the scraper"""
        self.print_header()
        jobs = await self.fetch_jobs()
        # Filter out any None values
        jobs = [j for j in jobs if j is not None]
        await self.save_results(jobs)
        return jobs
