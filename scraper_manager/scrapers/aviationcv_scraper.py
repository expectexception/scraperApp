from playwright.async_api import Page, async_playwright
import asyncio
from datetime import datetime
from .base_scraper import BaseScraper
import os

class AviationCVScraper(BaseScraper):
    def __init__(self, config, db_manager=None):
        super().__init__(config, 'aviationcv', db_manager)
        self.site_name = "AviationCV"
        self.base_url = "https://www.aviationcv.com"
        self.jobs_url = "https://www.aviationcv.com/jobs"
        self.jobs = []

    async def fetch_jobs(self):
        # Try proxy if available (set PROXY_URL environment variable)
        proxy_url = os.getenv('PROXY_URL')
        proxy_config = None
        if proxy_url:
            proxy_config = {
                'server': proxy_url
            }
            print(f"Using proxy: {proxy_url}")

        async with async_playwright() as p:
            # Launch with proxy if configured
            launch_args = {
                'headless': True,
                'args': ['--disable-blink-features=AutomationControlled']
            }
            if proxy_config:
                launch_args['proxy'] = proxy_config

            browser = await p.chromium.launch(**launch_args)
            page, context = await self.setup_stealth_page(browser)

            try:
                # Go to jobs page
                print(f"Navigating to {self.jobs_url}")
                await page.goto(self.jobs_url, wait_until='domcontentloaded', timeout=60000)
                await self.dismiss_cookie_banner(page)
                
                job_count = 0
                page_num = 1
                
                while job_count < self.max_jobs:
                    print(f"Processing page {page_num}...")
                    
                    # Wait for job cards
                    try:
                        await page.wait_for_selector('div.jcl-job-teaser', timeout=10000)
                    except Exception:
                        print("No job cards found on this page.")
                        break
                    
                    # Get all job cards
                    cards = await page.query_selector_all('div.jcl-job-teaser')
                    print(f"Found {len(cards)} job cards on page {page_num}")
                    
                    if not cards:
                        break
                    
                    # Iterate through cards
                    for card in cards:
                        if job_count >= self.max_jobs:
                            break
                            
                        try:
                            # Extract basic info from card
                            title_el = await card.query_selector('.jcl-job-teaser-title a')
                            if not title_el:
                                continue
                                
                            title = await title_el.inner_text()
                            url_suffix = await title_el.get_attribute('href')
                            if url_suffix and not url_suffix.startswith('http'):
                                url = self.base_url + url_suffix
                            else:
                                url = url_suffix
                                
                            company_el = await card.query_selector('.jcl-job-teaser-company')
                            company = await company_el.inner_text() if company_el else "Unknown"
                            
                            location_el = await card.query_selector('.jcl-job-teaser-location span.popoverlist-no-list-item')
                            location = await location_el.inner_text() if location_el else "Multiple Locations"
                            
                            # Date parsing (simplified for now)
                            date_posted = None
                            date_el = await card.query_selector('.jobTeaser_jobTeaserDate__aNE0m')
                            if date_el:
                                date_text = await date_el.inner_text()
                                # Try to parse relative dates if needed, or just keep raw string for verify
                                date_posted = date_text.replace('Published:', '').strip()
                            
                            # Create initial job object
                            # self._create_basic_job is not in BaseScraper, need to create manually or generic helper
                            # BaseScraper doesn't have create_basic_job? Let's check. 
                            # It doesn't seem to have valid one in the viewed file.
                            # I will manually construct it.
                            job = {
                                'title': title,
                                'company': company,
                                'location': location,
                                'url': url,
                                'posted_date': date_posted,
                                'scrape_date': datetime.now().isoformat(),
                                'source': 'aviationcv',
                                'job_id': f"aviationcv-{job_count}-{datetime.now().timestamp()}"
                            }
                            
                            
                            # now fetch full description
                            print(f"  Fetching details for: {title}")
                            
                            # Open new page for details to avoid navigating main page away
                            # But wait, we are iterating elements handles. Navigating main page breaks them.
                            # MUST open new page.
                            detail_page = await context.new_page()
                            try:
                                await detail_page.goto(url, wait_until='domcontentloaded', timeout=30000)
                                job['description'] = await self.extract_description_from_page(detail_page)
                            except Exception as e:
                                print(f"Error loading detail page: {e}")
                            finally:
                                await detail_page.close()
                            
                            self.jobs.append(job)
                            job_count += 1
                            
                        except Exception as e:
                            print(f"Error processing card: {e}")
                            continue
                    
                    # Next Page
                    next_btn = await page.query_selector('a[data-testid="pager_next"]')
                    if next_btn and job_count < self.max_jobs:
                        print("Going to next page...")
                        await next_btn.click()
                        await page.wait_for_load_state('domcontentloaded')
                        await asyncio.sleep(2) # brief pause
                        page_num += 1
                    else:
                        print("No more pages or limit reached.")
                        break
            
            finally:
                await browser.close()
                    
        return self.jobs

    async def extract_description_from_page(self, page: Page) -> str:
        """Extracts the job description from a given page."""
        try:
            # Extract description
            # Based on typical layouts, look for main content
            desc_el = await page.query_selector('.job-description, .job-details, article, main')
            if desc_el:
                return await desc_el.inner_text()
            else:
                # Fallback to body text
                return await page.inner_text('body')
        except Exception as e:
            print(f"Error extracting description: {e}")
            return ""

    async def dismiss_cookie_banner(self, page: Page):
        """Dismiss common cookie banners"""
        try:
            # Generic selectors often used
            selectors = [
                 '#onetrust-accept-btn-handler',
                 'button.accept-cookies',
                 'button:has-text("Accept")',
                 'button:has-text("Allow")',
                 '.cookie-banner button'
            ]
            for sel in selectors:
                if await page.is_visible(sel):
                    await page.click(sel)
                    break
        except Exception:
            pass

    # Helper not needed if inherited, but inheriting explicit "run" method for scheduling might be needed?
    # BaseScraper says "Subclasses must implement run() method".
    # I should implement run() which calls fetch_jobs + save_results.
    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        await self.save_results(jobs)
        return jobs

