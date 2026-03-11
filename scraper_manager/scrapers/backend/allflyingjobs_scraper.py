import asyncio
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from playwright.async_api import Page
from .base_scraper import BaseScraper

class AllFlyingJobsScraper(BaseScraper):
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key='allflyingjobs', db_manager=db_manager)
        self.base_url = "https://www.allflyingjobs.com"
        self.jobs = []

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        scraper_config = self.config.get('scrapers', {}).get(self.site_key, {})
        search_queries = scraper_config.get('search_queries', [])
        if not search_queries:
            print(f"No search queries configured for {self.site_key}. Please add 'search_queries' list to config.")
            return []

        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            # Launch with proxy if configured
            launch_args = {
                'headless': True,
                'args': ['--disable-blink-features=AutomationControlled']
            }
            # Try proxy if available (set PROXY_URL environment variable)
            proxy_url = os.getenv('PROXY_URL')
            if proxy_url:
                launch_args['proxy'] = {'server': proxy_url}
                print(f"Using proxy: {proxy_url}")
                
            browser = await p.chromium.launch(**launch_args)
            page, context = await self.setup_stealth_page(browser)
            
            for query in search_queries:
                print(f"Starting search for query: {query}")
                try:
                    await self._scrape_query(page, context, query)
                except Exception as e:
                    print(f"Error scraping query {query}: {e}")
                
        return self.jobs

    async def _scrape_query(self, page: Page, context, query: str):
        # Navigate to home
        print(f"Navigating to {self.base_url}")
        try:
            await page.goto(self.base_url, wait_until='domcontentloaded', timeout=60000)
        except Exception as e:
            print(f"Initial navigation failed: {e}. Retrying...")
            await asyncio.sleep(5)
            await page.goto(self.base_url, wait_until='domcontentloaded', timeout=60000)

        # Perform Search
        print(f"entering search query: {query}")
        await page.fill('#edit-s', query)
        
        # Click search and wait for navigation
        async with page.expect_navigation(timeout=60000, wait_until='domcontentloaded'):
            await page.click('#edit-submit-all-jobs-text-search')
            
        job_count = 0
        page_num = 1
        max_jobs = self.config.get('max_jobs', 50) or 50
        
        while len(self.jobs) < max_jobs:
            print(f"Processing page {page_num} for query '{query}' (Total: {len(self.jobs)}/{max_jobs})...")
            
            # Wait for results
            try:
                await page.wait_for_selector('div.views-row', timeout=10000)
            except:
                print("No jobs found on this page.")
                break

            # Get job cards
            cards = await page.query_selector_all('div.views-row')
            print(f"Found {len(cards)} job cards on page {page_num}")
            
            if not cards:
                break
                
            for card in cards:
                if len(self.jobs) >= max_jobs:
                    break
                    
                try:
                    # Extract Data
                    title_el = await card.query_selector('h3 a')
                    if not title_el:
                        continue
                        
                    title = await title_el.inner_text()
                    title = title.strip()
                    
                    if not self.should_process_job(title):
                        continue
                        
                    url = await title_el.get_attribute('href')
                    if url and not url.startswith('http'):
                        url = self.base_url + url
                        
                    company_el = await card.query_selector('.field-name-field-recruiter-name .field-item')
                    company = await company_el.inner_text() if company_el else "Unknown"
                    
                    location_el = await card.query_selector('.field-name-field-location .field-item')
                    if not location_el:
                        location_el = await card.query_selector('.field-name-field-base .field-item')
                    location = await location_el.inner_text() if location_el else "Location not specified"
                    
                    date_el = await card.query_selector('.teaserdate')
                    date_posted = await date_el.inner_text() if date_el else None
                    
                    # Create job object
                    job = {
                        'title': title,
                        'company': company,
                        'location': location,
                        'url': url,
                        'posted_date': date_posted,
                        'scrape_date': datetime.now().isoformat(),
                        'source': 'allflyingjobs',
                        'job_id': f"allflyingjobs-{job_count}-{datetime.now().timestamp()}"
                    }
                    
                    # Fetch description if URL is valid
                    if url:
                         print(f"  Fetching details for: {title}")
                         detail_page = await context.new_page()
                         try:
                             await detail_page.goto(url, wait_until='domcontentloaded', timeout=30000)
                             job['description'] = await self.extract_description_from_page(detail_page)
                         except Exception as e:
                             print(f"Error loading detail page: {e}")
                             job['description'] = "Failed to load description"
                         finally:
                             await detail_page.close()

                    self.jobs.append(job)
                    job_count += 1
                    
                except Exception as e:
                    print(f"Error processing card: {e}")

            # Check for next page
            if len(self.jobs) < max_jobs:
                next_btn = await page.query_selector('li.pager-next a')
                if next_btn:
                    print("Going to next page...")
                    async with page.expect_navigation(timeout=30000):
                        await next_btn.click()
                    page_num += 1
                else:
                    print("No more pages.")
                    break
            else:
                break

    async def extract_description_from_page(self, page: Page) -> str:
        # Generic description extraction
        # Try common selectors
        selectors = ['.field-name-body', '.job-description', 'div.content']
        for sel in selectors:
            el = await page.query_selector(sel)
            if el:
                return await el.inner_text()
        return await page.inner_text('body')

    async def run(self):
        print(f"--- Starting AllFlyingJobs Scraper ---")
        await self.fetch_jobs()
        await self.save_results(self.jobs)
        print(f"--- Finished AllFlyingJobs: {len(self.jobs)} jobs collected ---")
        return self.jobs
