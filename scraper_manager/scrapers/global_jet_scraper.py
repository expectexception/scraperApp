import asyncio
import logging
import re
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class GlobalJetScraper(BaseScraper):
    """
    Scraper for Global Jet.
    Works by iterating through the list and opening modals for each job.
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='global_jet', db_manager=db_manager)
        self.base_url = "https://globaljet.aero"
        self.jobs_url = "https://globaljet.aero/en/careers"
        self.company_name = "Global Jet"

    async def fetch_jobs(self) -> list:
        logger.info(f"[{self.site_key}] Navigating to {self.jobs_url} (Headless={self.headless})...")
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                # Navigate to careers page
                await page.goto(self.jobs_url, wait_until='networkidle', timeout=60000)
                await self.simulate_human_behavior(page)
                await self.random_delay(2, 4)
                
                # Wait for job items
                try:
                    await page.wait_for_selector('li.vacancies__item', timeout=20000)
                except Exception:
                    logger.warning(f"[{self.site_key}] No vacancy items found.")
                    return []

                # Get all vacancy items
                vacancy_items = await page.query_selector_all('li.vacancies__item')
                logger.info(f"[{self.site_key}] Found {len(vacancy_items)} vacancy items")
                
                # We need to click each item to see the description in a modal.
                # Since clicking might change the page state, we'll iterate carefully.
                for idx, item in enumerate(vacancy_items):
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    try:
                        # Re-query items to avoid stale elements if DOM changed
                        current_items = await page.query_selector_all('li.vacancies__item')
                        if idx >= len(current_items):
                            break
                        item = current_items[idx]
                        
                        # Extract title and location from the list item
                        title_elem = await item.query_selector('.text p')
                        loc_elem = await item.query_selector('li.vacancies__city p')
                        
                        title = (await title_elem.inner_text()).strip() if title_elem else "Unknown Title"
                        location = (await loc_elem.inner_text()).strip() if loc_elem else "Multi-Location"
                        
                        # Filter check before clicking (optimization)
                        if not self.should_process_job(title):
                            continue
                            
                        # Unique URL using hash if possible, or just a composite key
                        # The site uses hashes like #first-officer-falcon-8x7x
                        # We'll try to guess it or just use a unique ID
                        job_slug = re.sub(r'[^a-zA-Z0-9]', '-', title.lower())
                        job_url = f"{self.jobs_url}#{job_slug}"

                        if await self.is_url_already_scraped(job_url):
                            continue

                        logger.info(f"[{self.site_key}] Extracting: {title}")
                        
                        # Click the "More details" button
                        details_btn = await item.query_selector('.vacancies__link button')
                        if details_btn:
                            await details_btn.click()
                            # Wait for modal
                            modal_selector = '.offer_modal.js-modal.is-open'
                            try:
                                await page.wait_for_selector(modal_selector, timeout=5000)
                                desc_elem = await page.query_selector(f'{modal_selector} .__content')
                                description = (await desc_elem.inner_text()).strip() if desc_elem else ""
                                
                                # Close modal
                                close_btn = await page.query_selector('.button-close-modal.js-close-modal')
                                if close_btn:
                                    await close_btn.click()
                                    await asyncio.sleep(0.5)
                            except Exception as e:
                                logger.warning(f"[{self.site_key}] Could not open modal for {title}: {e}")
                                description = ""
                        else:
                            description = ""

                        job_id = f"globaljet_{idx}_{job_slug[:20]}"
                        
                        job = get_job_dict(
                            job_id=job_id,
                            title=title,
                            company=self.company_name,
                            location=location,
                            url=job_url,
                            source_url=self.jobs_url,
                            description=description,
                            source=self.site_key
                        )
                        jobs.append(job)
                        
                    except Exception as e:
                        logger.warning(f"[{self.site_key}] Error processing item {idx}: {e}")
                
            except Exception as e:
                logger.error(f"[{self.site_key}] Scraper error: {e}")
            finally:
                await context.close()
                await browser.close()
                
        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        
        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
