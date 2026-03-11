
import asyncio
from typing import Dict, Any, List
from playwright.async_api import Page, async_playwright
from datetime import datetime
from scraper_manager.scrapers.base_scraper import BaseScraper
import random

class AAAEScraper(BaseScraper):
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key='aaae', db_manager=db_manager)
        self.base_url = "https://careercenter.aaae.org"
        self.jobs_url = "https://careercenter.aaae.org/jobs"
        self.jobs = []

    async def fetch_jobs(self):
        async with async_playwright() as p:
            # Launch browser
            launch_args = {
                'headless': True,
                'args': ['--disable-blink-features=AutomationControlled']
            }
            if self.config.get('proxy'):
                launch_args['proxy'] = self.config['proxy']
            
            browser = await p.chromium.launch(**launch_args)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                print(f"Navigating to {self.jobs_url}")
                await page.goto(self.jobs_url, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(3) # Let cookie banners settle
                
                # Cookie Banner handling
                try:
                    await page.click('button:has-text("Got it")', timeout=5000)
                except:
                    pass

                job_count = 0
                processed_urls = set()
                
                while job_count < self.max_jobs:
                    # Get job cards
                    # Structure: div.bti-job-search-results > div.card
                    card_selector = 'div.bti-job-search-results div.card'
                    try:
                        await page.wait_for_selector(card_selector, timeout=20000)
                    except:
                        print("No jobs found on page (selector timeout)")
                        break
                        
                    cards = await page.query_selector_all(card_selector)
                    print(f"Found {len(cards)} cards on current view")
                    
                    new_cards_found = False
                    
                    for i, card in enumerate(cards):
                        if job_count >= self.max_jobs:
                            break
                            
                        try:
                            # Title and Link
                            # Selector: .card-title a
                            title_el = await card.query_selector(".card-title a")
                            if not title_el:
                                continue
                                
                            url_suffix = await title_el.get_attribute('href')
                            if not url_suffix:
                                continue
                                
                            full_url = self.base_url + url_suffix if not url_suffix.startswith('http') else url_suffix
                            
                            if full_url in processed_urls:
                                continue
                                
                            processed_urls.add(full_url)
                            new_cards_found = True
                            
                            title = await title_el.inner_text()
                            title = title.strip()
                            
                            if not self.should_scrape_job(title):
                                continue
                            
                            # Company
                            # Selector: .card-subtitle
                            company_el = await card.query_selector(".card-subtitle")
                            company = await company_el.inner_text() if company_el else "Unknown"
                            company = company.strip()
                            
                            # Location
                            # Selector: .card-text
                            location_el = await card.query_selector(".card-text")
                            location = await location_el.inner_text() if location_el else "Unknown"
                            location = location.strip()
                            
                            # Date is not in card, need to fetch details.
                            
                            job = {
                                'title': title,
                                'company': company,
                                'location': location,
                                'url': full_url,
                                'source': 'aaae',
                                'scrape_date': datetime.now().isoformat(),
                                'job_id': f"aaae-{url_suffix.split('/')[-1]}"
                            }
                            
                            # Fetch Description and Date using NEW PAGE context
                            print(f"  Fetching details: {title}")
                            detail_page = await context.new_page()
                            try:
                                await detail_page.goto(full_url, wait_until='domcontentloaded', timeout=30000)
                                job['description'] = await self.extract_description(detail_page)
                                
                                # Extract date from Detail Page
                                # Try 'Posted:' text search on body or specific container
                                body_text = await detail_page.inner_text('body')
                                if "Posted:" in body_text:
                                    import re
                                    match = re.search(r'Posted:\s*(.*?)(?:\n|$|\s{2,})', body_text)
                                    if match:
                                         job['posted_date'] = match.group(1).strip()
                                    else:
                                        job['posted_date'] = "Unknown"
                                else:
                                    job['posted_date'] = "Unknown"

                            except Exception as e:
                                print(f"Error fetching details: {e}")
                                job['description'] = ""
                                job['posted_date'] = "Unknown"
                            finally:
                                await detail_page.close()
                                
                            self.jobs.append(job)
                            job_count += 1
                            
                        except Exception as e:
                            print(f"Error processing card: {e}")
                            continue

                    # Pagination: Load More
                    # Selector: a.bti-job-search-load-more
                    if job_count < self.max_jobs:
                        load_more = await page.query_selector('a.bti-job-search-load-more')
                        if load_more and await load_more.is_visible():
                            print("Loading more jobs...")
                            await load_more.click()
                            await asyncio.sleep(5) # Wait for ajax load
                            
                            if not new_cards_found:
                                # Break if we clicked load more but found nothing new (avoid loop)
                                print("Load more clicked but no new unique jobs found.")
                                break
                        else:
                            print("No more 'Load More' button.")
                            break
                    else:
                        break

            finally:
                await browser.close()
        
        return self.jobs

    async def extract_description(self, page: Page):
        # AAAE detail page content
        # Often in .bti-job-detail-body or similar
        selectors = ['div.bti-job-detail-body', '#bti-job-detail-body', 'div.job-description']
        for sel in selectors:
            el = await page.query_selector(sel)
            if el:
                return await el.inner_text()
        return await page.inner_text('body')

    async def run(self):
        print(f"--- Starting AAAE Scraper ---")
        await self.fetch_jobs()
        await self.save_results(self.jobs)
        print(f"--- Finished AAAE Scraper: {len(self.jobs)} jobs collected ---")
        return self.jobs
