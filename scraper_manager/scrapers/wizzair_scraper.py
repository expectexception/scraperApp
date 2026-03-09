
import asyncio
import logging
import re
import json
from typing import List, Dict, Any
from datetime import datetime
from playwright.async_api import async_playwright, Page

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class WizzAirScraper(BaseScraper):
    """
    Scraper for Careers.wizzair.com
    Workflow:
    1. Search with keywords
    2. Extract results
    3. Pagination
    4. Detail extraction
    """
    
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key='wizzair', db_manager=db_manager)
        self.search_queries = config.get('search_queries', [''])
        self.search_url = config.get('jobs_url', "https://careers.wizzair.com/search/")
        
    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                # Iterate each query
                for query in self.search_queries:
                    if len(jobs) >= self.max_jobs:
                        break
                        
                    logger.info(f"[{self.site_key}] Searching for: '{query}'")
                    
                    # 1. Navigate to search page
                    await page.goto(self.search_url, wait_until='networkidle', timeout=60000)
                    await asyncio.sleep(2)
                    
                    # 2. Input Search
                    # Find input box
                    # Based on chunk, usually typical search inputs are input[type="text"] or specific id
                    # If query is empty, maybe just ensure list is loaded
                    if query:
                        try:
                            search_input = await page.query_selector('input[name="q"], input[type="search"], input[aria-label*="Search"]')
                            if search_input:
                                await search_input.fill(query)
                                await search_input.press('Enter')
                                await page.wait_for_load_state('networkidle')
                                await asyncio.sleep(3)
                        except Exception as e:
                            logger.warning(f"[{self.site_key}] Search interaction failed: {e}")
                    
                    # 3. Process results with pagination
                    current_page_num = 1
                    while len(jobs) < self.max_jobs:
                        # Wait for results to load
                        try:
                            await page.wait_for_selector('tr.data-row, tr.job-row, .job-card, .job-listing-item', timeout=10000)
                        except:
                            logger.debug(f"[{self.site_key}] Timeout waiting for job rows")
                            
                        # Extract jobs on current page using broader selectors
                        job_rows = await page.query_selector_all('tr.data-row, tr.job-row, tr[id*="job-result"], .job-card, .job-listing-item')
                        
                        if not job_rows:
                            # Fallback to all job links
                            job_links = await page.query_selector_all('a.jobTitle-link, a[href*="/job/"]:not([href*="facebook"]):not([href*="twitter"])')
                            rows_data = []
                            unique_urls = set()
                            for link in job_links:
                                href = await link.get_attribute('href')
                                title = await link.inner_text()
                                if href and title.strip() and "/job/" in href:
                                    f_url = "https://careers.wizzair.com" + href if href.startswith('/') else href
                                    if f_url not in unique_urls:
                                        unique_urls.add(f_url)
                                        rows_data.append({
                                            'url': f_url,
                                            'title': title.strip(),
                                            'location': "Unknown"
                                        })
                        else:
                            rows_data = []
                            for row in job_rows:
                                try:
                                    link_el = await row.query_selector('a.jobTitle-link, a[href*="/job/"]')
                                    # Specific SF location selectors
                                    loc_el = await row.query_selector('.jobLocation, .location, span[class*="location"]')
                                    
                                    if link_el:
                                        title = await link_el.inner_text()
                                        href = await link_el.get_attribute('href')
                                        location = "Unknown"
                                        if loc_el:
                                            # Strip the extra text if any
                                            location = await loc_el.inner_text()
                                            location = location.replace('\n', ' ').replace('\t', '').strip()
                                        
                                        rows_data.append({
                                            'url': "https://careers.wizzair.com" + href if href.startswith('/') else href,
                                            'title': title.strip(),
                                            'location': location
                                        })
                                except Exception as e:
                                    logger.debug(f"Row extraction failed: {e}")

                        logger.info(f"[{self.site_key}] Found {len(rows_data)} jobs on page {current_page_num}")
                        
                        if not rows_data:
                            logger.info(f"[{self.site_key}] No jobs found on page {current_page_num}, stopping.")
                            break

                        # Visit details
                        for item in rows_data:
                            if len(jobs) >= self.max_jobs:
                                break
                            
                            url = item['url']
                            if await self.is_url_already_scraped(url):
                                continue
                                
                            try:
                                # Visit detailed page
                                detail_page = await context.new_page()
                                await detail_page.goto(url, wait_until='networkidle', timeout=60000)
                                
                                title = item['title']
                                location = item['location']
                                
                                # Verify/update title from page if possible
                                page_title_el = await detail_page.query_selector('h1.jobTitle, h1#job-title, .jobTitle, h1')
                                if page_title_el:
                                    page_title = await page_title_el.inner_text()
                                    if page_title and len(page_title) > 5 and "APPLY NOW" not in page_title.upper():
                                        title = page_title.strip()
                                    else:
                                        # Use OG title
                                        og_title_el = await detail_page.query_selector('meta[property="og:title"]')
                                        if og_title_el:
                                            og_title = await og_title_el.get_attribute('content')
                                            if og_title:
                                                title = og_title.strip()
                                
                                # Clean title if still problematic
                                if "APPLY NOW" in title.upper():
                                    try:
                                        html_title = await detail_page.title()
                                        if html_title:
                                            title = html_title.split('|')[0].replace('Job Details', '').strip()
                                    except:
                                        pass

                                logger.info(f"[{self.site_key}] Processing: {title}")
                                
                                # Description
                                description = await self.extract_description_from_page(detail_page)
                                
                                # If description is empty, wait a bit and try again (SPAs)
                                if not description or len(description) < 200:
                                    await asyncio.sleep(2)
                                    description = await self.extract_description_from_page(detail_page)
                                
                                # Location & Company
                                if not location or location == "Unknown":
                                    loc_el = await detail_page.query_selector('.jobLocation, .facility, .location, span.custom-field')
                                    if loc_el:
                                        location = (await loc_el.inner_text()).strip()
                                    else:
                                        # Use json-ld if available
                                        try:
                                            script_el = await detail_page.query_selector('script[type="application/ld+json"]')
                                            if script_el:
                                                js_data = await script_el.innerText() # Wait, innerText vs inner_text? I'll use evaluate
                                                js_data = await detail_page.evaluate('el => el.innerText', script_el)
                                                data = json.loads(js_data)
                                                if isinstance(data, dict) and 'jobLocation' in data:
                                                    loc_data = data['jobLocation']
                                                    if isinstance(loc_data, dict) and 'address' in loc_data:
                                                        addr = loc_data['address']
                                                        parts = [addr.get('addressLocality'), addr.get('addressCountry')]
                                                        location = ", ".join([p for p in parts if p])
                                        except:
                                            pass
                                
                                company = "Wizz Air"
                                
                                # Apply Link
                                apply_url = url
                                apply_btn = await detail_page.query_selector('a[class*="apply"], a:has-text("Apply")')
                                if apply_btn:
                                    href = await apply_btn.get_attribute('href')
                                    if href:
                                        if href.startswith('/'):
                                             apply_url = "https://careers.wizzair.com" + href
                                        elif href.startswith('http'):
                                             apply_url = href
                                
                                job_data = {
                                    'company': company,
                                    'title': title.strip(),
                                    'location': location,
                                    'description': description,
                                    'source_url': url,
                                    'apply_url': apply_url,
                                    'url': url,
                                    'posted_date': datetime.now().isoformat(),
                                    'is_active': True
                                }
                                
                                jobs.append(job_data)
                                await detail_page.close()
                                
                            except Exception as e:
                                logger.error(f"[{self.site_key}] detail error {url}: {e}")
                                if 'detail_page' in locals():
                                    await detail_page.close()
                                    
                        # Pagination - Next Page by Number
                        if len(jobs) >= self.max_jobs:
                            break
                        
                        next_page_num = current_page_num + 1
                        next_selector = f'a[title="Page {next_page_num}"]'
                        next_el = await page.query_selector(next_selector)
                        
                        if next_el:
                            logger.info(f"[{self.site_key}] Navigating to page {next_page_num}...")
                            await next_el.click()
                            current_page_num = next_page_num
                            await page.wait_for_load_state('networkidle')
                            await asyncio.sleep(3)
                        else:
                            logger.info(f"[{self.site_key}] No more pages found after page {current_page_num}.")
                            break
                            
            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
                
        return jobs

    async def run(self):
        """Main entry point"""
        self.print_header()
        jobs = await self.fetch_jobs()
        await self.save_results(jobs)
        return jobs
