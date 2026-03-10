import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class CathayPacificScraper(BaseScraper):
    """
    Scraper for Cathay Pacific Careers
    URL: https://careers.cathaypacific.com/en/careers/jobs
    """
    
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key='cathay', db_manager=db_manager)
        self.base_url = "https://careers.cathaypacific.com/en/careers/jobs?keyword=&sortby=relevance&page=1"
        self.company_name = "Cathay Pacific"
        
    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Scrape jobs from Cathay Pacific careers page
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
                    
                    # Wait for job list
                    await page.wait_for_selector('a.search-listing__item', timeout=20000)
                    
                    # Accept cookies if needed (generic check)
                    try:
                        await page.locator('.cookie-consent-accept-all').click(timeout=3000)
                    except:
                        pass
                        
                except Exception as e:
                    logger.error(f"[{self.site_key}] Navigation/Loading failed: {e}")
                    return []
                
                while True:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    # Get visible jobs
                    job_items = await page.locator('a.search-listing__item').all()
                    logger.info(f"[{self.site_key}] Found {len(job_items)} jobs on current page")
                    
                    for item in job_items:
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break
                            
                        try:
                            # Title
                            title_el = item.locator('.search-listing__item__title')
                            if not await title_el.count():
                                continue
                            title = await title_el.text_content()
                            title = title.strip()
                            
                            # Location - let's check the HTML structure
                            loc_el = item.locator('.search-listing__item__info span').first
                            location = await loc_el.text_content() if await loc_el.count() else "Unknown Location"
                            
                            # Link
                            link = await item.get_attribute('href')
                            if not link:
                                continue
                                
                            if location == "Unknown Location" or not location:
                                # Try extracting from the job URL path instead as fallback
                                try:
                                    parts = link.split('/')
                                    if 'jobs' in parts:
                                        idx = parts.index('jobs')
                                        if len(parts) > idx + 1:
                                            location = parts[idx + 1].replace('-', ' ').title()
                                except:
                                    pass

                            location = location.strip()
                            
                            # Ensure full URL
                            if not link.startswith('http'):
                                link = f"https://careers.cathaypacific.com{link}"
                                
                            job = {
                                'company': self.company_name,
                                'title': title,
                                'location': location,
                                'url': link,
                                'source_url': link,
                                'apply_url': link, # Redirects to talentlink, handled in detail or just use this
                                'is_active': True,
                                'description': ''
                            }
                            
                            jobs.append(job)
                            
                        except Exception as e:
                            logger.warning(f"[{self.site_key}] Error parsing job item: {e}")
                            continue

                    # Pagination Logic
                    # Look for Next button
                    next_btn = page.locator('a.pagination__item--next')
                    
                    if await next_btn.is_visible(): 
                        # Check if disabled by class or href
                        classes = await next_btn.get_attribute('class') or ''
                        if 'disabled' in classes.lower():
                             logger.info(f"[{self.site_key}] Next button disabled. Reached end.")
                             break
                             
                        logger.info(f"[{self.site_key}] Navigating to next page...")
                        await next_btn.click()
                        
                        # Wait for content to update
                        await page.wait_for_timeout(3000)
                        await page.wait_for_selector('a.search-listing__item', timeout=10000)
                        
                    else:
                        logger.info(f"[{self.site_key}] No next button found. Reached end.")
                        break

                # Detail Extraction
                logger.info(f"[{self.site_key}] Extracting details for {len(jobs)} jobs...")
                for job in jobs:
                    if not job['url']:
                        continue
                        
                    try:
                        detail_page = await context.new_page()
                        await detail_page.goto(job['url'], wait_until='domcontentloaded', timeout=30000)
                        
                        # Description
                        # Analysis: div.job-details__content
                        desc_el = detail_page.locator('.job-details__content')
                        # Sometimes description is in .job-details__left
                        if not await desc_el.count():
                             desc_el = detail_page.locator('.job-details__left')
                             
                        if await desc_el.count():
                            job['description'] = await desc_el.inner_html()
                        else:
                            # Fallback
                            job['description'] = await detail_page.content()
                            
                        # Apply Link
                        # Analysis: a[title='Apply Now'] or similar
                        apply_btn = detail_page.locator("a[title='Apply Now']")
                        if await apply_btn.count():
                             href = await apply_btn.first.get_attribute('href')
                             if href:
                                 job['apply_url'] = href if href.startswith('http') else f"https://careers.cathaypacific.com{href}"
                        
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
