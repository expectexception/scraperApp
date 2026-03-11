import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class BritishAirwaysScraper(BaseScraper):
    """
    Scraper for British Airways Careers
    URL: https://careers.ba.com/search-jobs
    """
    
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key='ba', db_manager=db_manager)
        self.base_url = "https://careers.ba.com/search-jobs"
        self.company_name = "British Airways"
        
    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Scrape jobs from British Airways careers page
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
                    
                    # Accept cookies
                    try:
                        await page.locator('#system-ialert-button').click(timeout=5000)
                    except:
                        pass
                        
                except Exception as e:
                    logger.error(f"[{self.site_key}] Navigation failed: {e}")
                    return []
                
                while True:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    # Get visible jobs
                    job_items = await page.locator('li.job-list--list-item').all()
                    logger.info(f"[{self.site_key}] Found {len(job_items)} jobs on current page")
                    
                    for item in job_items:
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break
                            
                        try:
                            # Title
                            title_el = item.locator('.job-list--link .job-list--title')
                            # If the specific class isn't there, try generic p but restrict to first
                            if not await title_el.count():
                                title_el = item.locator('.job-list--link p').first
                                
                            if not await title_el.count():
                                continue
                                
                            title = await title_el.text_content()
                            title = title.strip()
                            
                            # Location - specific class .job-location
                            loc_el = item.locator('.job-list--link span.job-location')
                            if not await loc_el.count():
                                # Fallback: try finding text node in link excluding button
                                loc_el = item.locator('.job-list--link span').first
                                
                            location = await loc_el.text_content() if await loc_el.count() else "Unknown Location"
                            location = location.replace('Location:', '').strip()
                            
                            # Link
                            link_el = item.locator('a.job-list--link')
                            link = await link_el.get_attribute('href')
                            
                            if not link:
                                continue
                                
                            # Ensure full URL
                            if not link.startswith('http'):
                                link = f"https://careers.ba.com{link}" if link.startswith('/') else f"https://careers.ba.com/{link}"
                                
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
                    # Look for Next button in .pagination-paging .next
                    next_btn = page.locator('.pagination-paging .next')
                    
                    if await next_btn.is_visible(): 
                        # Check if it's disabled (sometimes class has 'disabled', or just check visual state)
                        # BA site usually hides Next if not available or disables it.
                        # Check href attribute usually exists if enabled
                        href = await next_btn.get_attribute('href')
                        if not href or href == '#':
                            logger.info(f"[{self.site_key}] Next button has no link. Reached end.")
                            break
                            
                        logger.info(f"[{self.site_key}] Navigating to next page...")
                        
                        # Click and wait for new content
                        current_first_job = await page.locator('li.job-list--list-item').first.text_content()
                        
                        await next_btn.click()
                        
                        # Wait for job list to update (naive wait or check for change)
                        try:
                           await page.wait_for_timeout(2000) # Basic wait
                           # Could wait for first job text to change
                        except:
                           pass
                           
                    else:
                        logger.info(f"[{self.site_key}] No next button found. Reached end.")
                        break

                # Detail Extraction
                logger.info(f"[{self.site_key}] Extracting details for {len(jobs)} jobs...")
                for job in jobs:
                    if not job['url']:
                        continue
                        
                    if not self.should_process_job(job['title']):
                        continue
                        
                    try:
                        detail_page = await context.new_page()
                        await detail_page.goto(job['url'], wait_until='domcontentloaded', timeout=30000)
                        
                        # Description
                        # Usually in a main content area. Using generic locator based on analysis or extensive select
                        # Analysis said .job-detail or main content
                        desc_el = detail_page.locator('.job-detail')
                        if await desc_el.count():
                            job['description'] = await desc_el.inner_html()
                        else:
                            # Fallback
                            job['description'] = await detail_page.content()
                        
                        # Apply Link
                        # Analysis said a.ajd_btn__apply
                        apply_btn = detail_page.locator('a.ajd_btn__apply')
                        if await apply_btn.count():
                             href = await apply_btn.first.get_attribute('href')
                             if href:
                                 job['apply_url'] = href if href.startswith('http') else f"https://careers.ba.com{href}"
                        
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
        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
