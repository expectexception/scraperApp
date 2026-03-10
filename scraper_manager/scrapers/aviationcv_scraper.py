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
                    
                    page_jobs = []
                    # First pass: Extract titles and URLs for pre-filtering
                    for card in cards:
                        try:
                            title_el = await card.query_selector('.jcl-job-teaser-title a')
                            if not title_el: continue
                            
                            title = (await title_el.inner_text()).strip()
                            url_suffix = await title_el.get_attribute('href')
                            url = self.base_url + url_suffix if url_suffix and not url_suffix.startswith('http') else url_suffix
                            
                            company_el = await card.query_selector('.jcl-job-teaser-company')
                            company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                            
                            location_el = await card.query_selector('.jcl-job-teaser-location span.popoverlist-no-list-item')
                            location = (await location_el.inner_text()).strip() if location_el else "Multiple Locations"
                            
                            date_el = await card.query_selector('.jobTeaser_jobTeaserDate__aNE0m')
                            date_posted = date_el.inner_text() if date_el else None
                            if date_posted: date_posted = (await date_posted).replace('Published:', '').strip()
                            
                            page_jobs.append({
                                'title': title,
                                'url': url,
                                'company': company,
                                'location': location,
                                'date_posted': date_posted,
                                'card_el': card # Keep reference for some consistency if needed, though we use URL for details
                            })
                        except Exception:
                            continue

                    print(f"Applying pre-filter to {len(page_jobs)} jobs on page {page_num}...")
                    matched_page_jobs, _, _ = self.apply_title_filter(page_jobs)
                    print(f"{len(matched_page_jobs)} jobs passed pre-filtering. Fetching details...")

                    # Second pass: Fetch details only for matched jobs
                    for job_meta in matched_page_jobs:
                        if job_count >= self.max_jobs:
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
                                    'source': 'aviationcv',
                                    'job_id': f"aviationcv-{job_count}-{datetime.now().timestamp()}",
                                    'description': description
                                }
                                self.jobs.append(job)
                                job_count += 1
                            except Exception as e:
                                print(f"Error loading detail page: {e}")
                            finally:
                                await detail_page.close()
                            
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

