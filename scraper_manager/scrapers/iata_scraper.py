
import asyncio
import logging
import random
import re
import json
from typing import List, Dict, Any
from datetime import datetime
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class IataScraper(BaseScraper):
    """
    Scraper for IATA (International Air Transport Association)
    Uses Playwright to intercept internal API calls for job data
    """
    
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key='iata', db_manager=db_manager)
        self.jobs_url = "https://iata.csod.com/ux/ats/careersite/1/home?c=iata"
        
    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Scrape jobs from IATA using network interception with DOM fallback
        """
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            # captured_jobs will hold data from API interception
            captured_jobs = []
            
            # Setup response listener
            async def handle_response(response):
                if "rec-job-search/external/jobs" in response.url and response.request.method == "POST":
                    try:
                        data = await response.json()
                        logger.info(f"[{self.site_key}] Intercepted payload keys: {list(data.keys()) if data else 'None'}")
                        if data and 'data' in data:
                            jobs_list = data['data'].get('jobs', [])
                            logger.info(f"[{self.site_key}] Jobs in 'data.jobs': {len(jobs_list)}")
                            captured_jobs.extend(jobs_list)
                        elif data and 'jobs' in data:
                             captured_jobs.extend(data['jobs'])
                             logger.info(f"[{self.site_key}] Jobs in 'jobs': {len(data['jobs'])}")
                        else:
                             logger.warning(f"[{self.site_key}] Unexpected JSON structure: {str(data)[:200]}")
                    except Exception as e:
                        logger.warning(f"[{self.site_key}] Error parsing API response: {e}")

            page.on("response", handle_response)
            
            try:
                logger.info(f"[{self.site_key}] Navigating to {self.jobs_url}")
                await page.goto(self.jobs_url, wait_until='networkidle', timeout=60000)
                
                # Wait for initial data load
                await asyncio.sleep(5)
                
                # Check if we have captured jobs - if not, trigger search
                if not captured_jobs:
                    logger.warning(f"[{self.site_key}] No jobs captured via API, triggered search...")
                    try:
                        search_input = await page.query_selector('input[placeholder*="Search"], input[aria-label*="Search"], input[type="search"]')
                        if search_input:
                            await search_input.fill(" ")
                            await search_input.press("Enter")
                            logger.info(f"[{self.site_key}] Triggered search with space")
                            await page.wait_for_load_state('networkidle')
                            await asyncio.sleep(5)
                    except Exception as e:
                        logger.warning(f"[{self.site_key}] Error triggering search: {e}")

                # If still no jobs, try DOM fallback
                if not captured_jobs:
                    logger.warning(f"[{self.site_key}] API failed, trying DOM fallback")
                    try:
                        await page.wait_for_selector('li[data-requisition-id], div[data-requisition-id], a[href*="/requisition/"]', timeout=5000)
                    except:
                        pass
                        
                    job_cards = await page.query_selector_all('li[data-requisition-id], div[data-requisition-id]')
                    if not job_cards:
                        links = await page.query_selector_all('a[href*="/requisition/"]')
                        for link in links:
                            href = await link.get_attribute('href')
                            if href and '/requisition/' in href:
                                req_id_match = re.search(r'/requisition/(\d+)', href)
                                if req_id_match:
                                    req_id = req_id_match.group(1)
                                    title = await link.inner_text()
                                    captured_jobs.append({
                                        'requisitionId': req_id,
                                        'title': title.strip(),
                                        'fallback': True
                                    })
                    else:
                        for card in job_cards:
                            req_id = await card.get_attribute('data-requisition-id')
                            title_el = await card.query_selector('h3, h4, a[class*="title"]')
                            title = await title_el.inner_text() if title_el else "Unknown Job"
                            
                            # Try to get location from card
                            location = "Unknown"
                            loc_el = await card.query_selector('span[class*="location"], div[class*="location"]')
                            if not loc_el:
                                # Fallback: search all divs/spans in card
                                loc_el = await card.query_selector('div:not(:has(h3,h4)), span:not(:has(a))')
                            
                            if loc_el:
                                location = await loc_el.inner_text()
                            
                            captured_jobs.append({
                                'requisitionId': req_id,
                                'title': title.strip(),
                                'location': location.strip() if location else "Unknown",
                                'fallback': True
                            })
                    logger.info(f"[{self.site_key}] DOM Fallback found {len(captured_jobs)} jobs")

                processed_ids = set()
                page_num = 1
                no_new_jobs_count = 0
                
                while len(jobs) < self.max_jobs and no_new_jobs_count < 3:
                    current_batch = [j for j in captured_jobs if j.get('requisitionId') not in processed_ids]
                    
                    if not current_batch:
                        if not any(j.get('fallback') for j in captured_jobs):
                            try:
                                next_btn = await page.query_selector('button[aria-label="Next Page"], .pagination-next')
                                if next_btn and await next_btn.is_enabled():
                                    logger.info(f"[{self.site_key}] navigating to next page...")
                                    await next_btn.click()
                                    await page.wait_for_load_state('networkidle')
                                    await asyncio.sleep(3)
                                    continue
                            except:
                                pass
                        
                        no_new_jobs_count += 1
                        await asyncio.sleep(2)
                        continue

                    for job_entry in current_batch:
                        if len(jobs) >= self.max_jobs:
                            break
                            
                        job_id = job_entry.get('requisitionId')
                        if job_id in processed_ids:
                            continue
                        processed_ids.add(job_id)
                        
                        try:
                            # Handle both API and Fallback data
                            title = job_entry.get('title', 'Unknown Title')
                            req_id = job_entry.get('requisitionId')
                            url = f"https://iata.csod.com/ux/ats/careersite/1/home/requisition/{req_id}?c=iata"
                            
                            if await self.is_url_already_scraped(url):
                                continue
                                
                            logger.info(f"[{self.site_key}] Processing: {title}")
                            
                            description = job_entry.get('description', '')
                            location = job_entry.get('location', 'Unknown')
                            country_code = None
                            
                            # Locations logic (API only)
                            locations = job_entry.get('locations', [])
                            if locations:
                                loc_data = locations[0]
                                parts = [x for x in [loc_data.get('city'), loc_data.get('state'), loc_data.get('country')] if x]
                                location = ", ".join(parts)
                                if loc_data.get('country'):
                                    country_code = loc_data.get('country')[:2].upper()
                            
                            # If fallback or missing desc/loc, visit page
                            if not description or len(description) < 100 or location == "Unknown":
                                detail_page = await context.new_page()
                                try:
                                    logger.info(f"[{self.site_key}] Navigating to detail: {url}")
                                    await detail_page.goto(url, wait_until='networkidle', timeout=60000)
                                    
                                    # Wait for job description - common CSOD selectors
                                    try:
                                        await detail_page.wait_for_selector('.cs-at-job-description, div[data-name="jobDescription"], .job-description', timeout=10000)
                                    except:
                                        logger.debug(f"[{self.site_key}] Timeout waiting for specific description selector")
                                        
                                    desc_el = await detail_page.query_selector('.cs-at-job-description, div[data-name="jobDescription"], .job-description, .c-job-description-details')
                                    if desc_el:
                                        description = await desc_el.inner_text()
                                    else:
                                        description = await self.extract_description_from_page(detail_page)
                                    
                                    # Extract location from page if unknown
                                    if not location or location == "Unknown":
                                        try:
                                            # Search for common CSS selectors for location in CSOD
                                            loc_selectors = [
                                                '.cs-at-job-detail-location', 
                                                'div[data-name="location"]', 
                                                'span[data-name="location"]',
                                                '.requisition-info-item',
                                                'div[class*="location"]',
                                                'span[class*="location"]'
                                            ]
                                            for sel in loc_selectors:
                                                loc_el = await detail_page.query_selector(sel)
                                                if loc_el:
                                                    text = (await loc_el.inner_text()).strip()
                                                    if text and "req" not in text.lower():
                                                        location = text
                                                        break
                                            
                                            if not location or location == "Unknown":
                                                # Try the "City, Country | req1234" header pattern from the description itself
                                                if title in description:
                                                    parts = description.split('|')
                                                    if len(parts) > 1:
                                                        header = parts[0]
                                                        if title in header:
                                                            loc = header.replace(title, '').strip()
                                                            if loc:
                                                                location = loc
                                                
                                            if not location or location == "Unknown":
                                                # Final fallback: generic body search
                                                body_text = await detail_page.inner_text('body')
                                                loc_match = re.search(r'Location:\s*([^\n|]+)', body_text)
                                                if loc_match:
                                                    location = loc_match.group(1).strip()
                                        except:
                                            pass
                                    
                                    # Clean up title from description if it leads
                                    if description.startswith(title):
                                        # But keep description content! Only remove the title-header if it looks redundant
                                        pass
                                except Exception as e:
                                    logger.warning(f"[{self.site_key}] Failed to get detail: {e}")
                                finally:
                                    await detail_page.close()

                            jobs.append({
                                'company': 'IATA',
                                'title': title,
                                'location': location,
                                'country_code': country_code,
                                'description': description,
                                'source_url': url,
                                'apply_url': url,
                                'url': url,
                                'posted_date': datetime.now().isoformat(),
                                'is_active': True,
                                'raw_json': job_entry
                            })
                            
                        except Exception as e:
                            logger.error(f"[{self.site_key}] Job error: {e}")
                            
            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
                
        return jobs

    async def run(self):
        """Main entry point"""
        self.print_header()
        jobs = await self.fetch_jobs()
        await self.save_results(jobs)
        return jobs

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='IATA Scraper')
    parser.add_argument('--max-jobs', type=int, default=10, help='Maximum jobs to scrape')
    parser.add_argument('--verbose', action='store_true', help='Verbose mapping')
    args = parser.parse_args()
    
    config = {
        'scrapers': {
            'iata': {
                'max_jobs': args.max_jobs
            }
        }
    }
    
    scraper = IataScraper(config)
    asyncio.run(scraper.run())
