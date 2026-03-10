import asyncio
import random
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Page

from scraper_manager.scrapers.base_scraper import BaseScraper

class JSFirmScraper(BaseScraper):
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key='jsfirm', db_manager=db_manager)
        self.base_url = "https://www.jsfirm.com"
        self.search_url = "https://www.jsfirm.com/search" # Using home for initial nav
        self.jobs = []
        
    async def fetch_jobs(self):
        # Try proxy if available
        proxy_url = os.getenv('PROXY_URL')
        proxy_config = None
        if proxy_url:
            proxy_config = {'server': proxy_url}
            print(f"Using proxy: {proxy_url}")

        async with async_playwright() as p:
            launch_args = {
                'headless': True,
                'args': ['--disable-blink-features=AutomationControlled']
            }
            if proxy_config:
                launch_args['proxy'] = proxy_config

            browser = await p.chromium.launch(**launch_args)
            page, context = await self.setup_stealth_page(browser)

            try:
                # We will search just one location for now, or loop if configured.
                # Assuming 'location' might be in config, defaulting to 'Florida' as per request context
                # In a real scenario, this might loop through a list.
                locations = self.site_config.get('search_locations', ['Florida'])
                
                for location in locations:
                    print(f"Starting search for location: {location}")
                    await self._scrape_location(page, context, location)
                    
            finally:
                await browser.close()
                
        return self.jobs

    async def _scrape_location(self, page: Page, context, location: str):
        # Navigate to home to start clean search
        print(f"Navigating to {self.base_url}")
        try:
            await page.goto(self.base_url, wait_until='domcontentloaded', timeout=90000)
        except Exception as e:
            print(f"Initial navigation failed: {e}. Retrying once...")
            await asyncio.sleep(5)
            await page.goto(self.base_url, wait_until='domcontentloaded', timeout=90000)
        
        # Input location
        loc_input = '#ctl00_ctl00_ucQuickJobSearch_txtWhere_Input'
        search_btn = '#ucQuickJobSearch_btnSearchJobs'
        
        try:
            await page.wait_for_selector(loc_input, timeout=10000)
            print(f"Entering location: {location}")
            await page.fill(loc_input, location)
            await asyncio.sleep(1) # Wait for UI to settle
            
            print("Clicking search...")
            # Click and wait for navigation or new content
            # JSFirm seems to do a full page reload or postback.
            # Using asyncio.gather to ensure we catch the navigation event if it happens
            async with page.expect_navigation(timeout=60000, wait_until='domcontentloaded'):
                await page.click(search_btn)
            
            # Wait for results container specifically
            try:
                await page.wait_for_selector('div.welljob', timeout=30000)
            except Exception:
                print("Warning: Results container not found immediately.")
            
        except Exception as e:
            print(f"Error performing search for {location}: {e}")
            # Try to continue anyway, maybe results are already there or page just reloaded
            pass

        # Pagination loop
        job_count = 0
        page_num = 1
        
        while len(self.jobs) < self.max_jobs:
            print(f"Processing page {page_num} for {location} (Total jobs: {len(self.jobs)}/{self.max_jobs})...")
            
            # Wait for job cards
            try:
                # job cards are usually in div.welljob (from analysis)
                await page.wait_for_selector('div.welljob', timeout=10000)
            except Exception:
                print("No job cards found on this page.")
                break
            
            cards = await page.query_selector_all('div.welljob')
            print(f"Found {len(cards)} job cards on page {page_num}")
            
            if not cards:
                break
                
            page_jobs = []
            # First pass: Extract initial info for pre-filtering
            for card in cards:
                try:
                    title_el = await card.query_selector('a.u:not(.company)')
                    if not title_el: continue
                    title = (await title_el.inner_text()).strip()
                    url_suffix = await title_el.get_attribute('href')
                    url = self.base_url + url_suffix if url_suffix and not url_suffix.startswith('http') else url_suffix
                    
                    company_el = await card.query_selector('a.u.company')
                    company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                    
                    col_8 = await card.query_selector('div.col-xs-8')
                    location = "Unknown"
                    if col_8:
                        text_content = await col_8.inner_text()
                        lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                        if lines: location = lines[-1]
                            
                    date_el = await card.query_selector('span.text-muted')
                    date_posted = (await date_el.inner_text()).strip() if date_el else "Unknown"

                    page_jobs.append({
                        'title': title,
                        'url': url,
                        'company': company,
                        'location': location,
                        'date_posted': date_posted
                    })
                except Exception:
                    continue

            print(f"Applying pre-filter to {len(page_jobs)} jobs on page {page_num}...")
            matched_page_jobs, _, _ = self.apply_title_filter(page_jobs)
            print(f"{len(matched_page_jobs)} jobs passed pre-filtering. Fetching details...")

            for job_meta in matched_page_jobs:
                if len(self.jobs) >= self.max_jobs:
                    break
                
                try:
                    title = job_meta['title']
                    url = job_meta['url']
                    
                    print(f"  Fetching details for: {title}")
                    detail_page = await context.new_page()
                    try:
                        await detail_page.goto(url, wait_until='domcontentloaded', timeout=30000)
                        description = await self.extract_description_from_page(detail_page)
                        
                        job = {
                            'title': title,
                            'company': job_meta['company'],
                            'location': job_meta['location'],
                            'url': url,
                            'posted_date': job_meta['date_posted'],
                            'scrape_date': datetime.now().isoformat(),
                            'source': 'jsfirm',
                            'job_id': f"jsfirm-{len(self.jobs)}-{datetime.now().timestamp()}",
                            'description': description
                        }
                        self.jobs.append(job)
                    except Exception as e:
                        print(f"Error fetching details: {e}")
                    finally:
                        await detail_page.close()
                    
                except Exception as e:
                    print(f"Error processing card: {e}")
                    
            # Next Page
            # Selector for '>>' button: a containing text ">>" inside table
            # It uses __doPostBack, so we need to wait for URL chage or Network Idle? 
            # Often URL doesn't change much but content does.
            # We can wait for the 'div.welljob' to become stale or count to change?
            # Easiest is waiting for networkidle after click.
            
            if len(self.jobs) < self.max_jobs:
                # Find the next button
                # tr.pagination-ys a with text >>
                # Playwright selector :text(">>")
                
                next_btn = await page.query_selector('tr.pagination-ys a:has-text(">>")')
                
                if next_btn:
                    print("Going to next page...")
                    # Capture first job title to check for change
                    first_card_title = ""
                    if cards:
                        try:
                            title_el = await cards[0].query_selector('a.u:not(.company)')
                            if title_el:
                                first_card_title = await title_el.inner_text()
                        except:
                            pass

                    await next_btn.evaluate("element => element.click()")
                    
                    # Wait for postback reload by checking if first card changed
                    try:
                        # Wait for a bit for the click to register
                        await asyncio.sleep(2)
                        
                        # Wait for new content
                        async def check_new_content():
                            start_time = datetime.now()
                            while (datetime.now() - start_time).seconds < 30:
                                try:
                                    new_cards = await page.query_selector_all('div.welljob')
                                    if not new_cards:
                                        await asyncio.sleep(0.5)
                                        continue
                                    
                                    new_title_el = await new_cards[0].query_selector('a.u:not(.company)')
                                    if new_title_el:
                                        new_title = await new_title_el.inner_text()
                                        if new_title != first_card_title:
                                            return True
                                except Exception as e:
                                    # Ignore errors during navigation (execution context destroyed)
                                    pass
                                await asyncio.sleep(0.5)
                            return False

                        if await check_new_content():
                            page_num += 1
                        else:
                             print("Warning: Content did not appear to change after pagination click.")
                             break
                    except Exception as e:
                        print(f"Error checking for new page content: {e}")
                        break
                    except Exception as e:
                        print(f"Error navigating to next page: {e}")
                        break
                else:
                    print("No next page button found.")
                    break
            else:
                break

    async def extract_description_from_page(self, page: Page):
        # Try to find the detailed description container
        # Often in a container like #job-description or similar.
        # Need to be generic or inspect a detail page.
        # Based on typical job sites, it's often the main text block.
        # Without specific inspection of detail page, we try common selectors.
        # Since we haven't inspected a detail page specifically, we'll strip known headers/footers
        # or grab the biggest text block.
        
        # For now, let's grab 'body' text but try to narrow it down if possible.
        # Let's try a few common content wrappers
        selectors = ['div.job-description', 'div.description', 'div#jobDescription', 'div.container.content']
        
        for sel in selectors:
            el = await page.query_selector(sel)
            if el:
                return await el.inner_text()
        
        # Fallback: Body text
        return await page.inner_text('body')

    async def run(self):
        print(f"--- Starting JSFirm Scraper ---")
        print(f"Max jobs: {self.config.get('max_jobs', 'Default')}")
        
        await self.fetch_jobs()
        await self.save_results(self.jobs)
        print(f"--- Finished JSFirm Scraper: {len(self.jobs)} jobs collected ---")
        return self.jobs
