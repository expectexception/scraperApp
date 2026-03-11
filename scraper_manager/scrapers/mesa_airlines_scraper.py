import asyncio
import logging
import json
import time
from typing import List, Dict, Optional
from .base_scraper import BaseScraper
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class MesaAirlinesScraper(BaseScraper):
    """Scraper for Mesa Airlines careers site using ADP portal via Playwright."""
    
    def __init__(self, config: Dict, db_manager=None):
        super().__init__(config, site_key='mesa', db_manager=db_manager)
        self.base_url = "https://myjobs.adp.com/mesaexternal/cx/job-listing"

    async def fetch_jobs(self) -> List[Dict]:
        """Fetch jobs from ADP portal using Playwright."""
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                
                # Intercept the API response to get full job data (including descriptions)
                api_response_data = []
                
                async def handle_response(response):
                    if "apply-custom-filters" in response.url and response.status == 200:
                        try:
                            data = await response.json()
                            api_response_data.append(data)
                        except Exception as e:
                            logger.error(f"[{self.site_key}] Error parsing API response: {e}")

                page.on("response", handle_response)
                
                await page.goto(self.base_url, wait_until="commit", timeout=60000)
                
                # Wait longer for ADP portal to settle
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(5)
                
                # Check for cookie banner/overlay
                try:
                    cookie_btn = await page.query_selector("button:has-text('Accept'), .optanon-allow-all-button")
                    if cookie_btn:
                        await cookie_btn.click()
                        logger.info(f"[{self.site_key}] Clicked cookie banner")
                except:
                    pass
                
                # Wait for the job list or the Search button
                try:
                    await page.wait_for_selector(".job-title-link, mat-expansion-panel", timeout=20000)
                except:
                    # Try to click search if nothing appeared
                    search_btn = await page.query_selector("button:has-text('Search')")
                    if search_btn:
                        await search_btn.click()
                        await page.wait_for_selector(".job-title-link", timeout=20000)
                
                # Give a small buffer for all requests to finish
                await asyncio.sleep(5)
                
                if api_response_data:
                    logger.info(f"[{self.site_key}] Captured API data for {len(api_response_data)} responses.")
                    
                    for data in api_response_data:
                        requisitions = data.get('jobRequisitions', [])
                        for req in requisitions:
                            title = req.get('jobTitle', '').strip()
                            req_id = req.get('reqId', '')
                            
                            if not title or not req_id:
                                continue
                                
                            # Early filtering
                            if not self.should_process_job(title):
                                continue
                                
                            # Duplicate check
                            job_url = f"{self.base_url}?reqId={req_id}" # ADP URLs vary, but reqId is key
                            if await self.is_url_already_scraped(job_url):
                                continue
                                
                            # Extract details
                            # Location
                            location = "Unknown"
                            locations = req.get('requisitionLocations', [])
                            if locations:
                                first_loc = locations[0]
                                if 'nameCode' in first_loc:
                                    location = first_loc['nameCode'].get('longName', 'Unknown')
                            
                            # Description
                            description_html = req.get('jobDescription', '')
                            qualifications = req.get('jobQualifications', '')
                            full_desc = f"{description_html}\n\n<h3>Qualifications</h3>\n{qualifications}"
                            
                            jobs.append({
                                'title': title,
                                'company': 'Mesa Airlines',
                                'location': location,
                                'url': job_url,
                                'description': full_desc,
                            })
                            
                            if self.max_jobs and len(jobs) >= self.max_jobs:
                                break
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break
                            
                else:
                    logger.warning(f"[{self.site_key}] No API data captured, falling back to DOM parsing...")
                    # Fallback DOM parsing if API interception failed
                    job_elements = await page.query_selector_all("mat-expansion-panel")
                    for el in job_elements:
                        title_el = await el.query_selector(".job-title-link span")
                        if not title_el: continue
                        title = await title_el.inner_text()
                        
                        if not self.should_process_job(title):
                            continue
                            
                        # More complex to get URL and description from DOM without clicking
                        # For now, we rely on the API as it's the standard for this portal
                        pass

                logger.info(f"[{self.site_key}] Successfully parsed {len(jobs)} jobs.")
                return jobs
                
            except Exception as e:
                logger.error(f"[{self.site_key}] Scraper failed: {e}")
                return jobs
            finally:
                await browser.close()

    async def run(self):
        """Standard run flow."""
        self.print_header()
        
        jobs = await self.fetch_jobs()
        
        # Filter and save
        matched_jobs, rejected_jobs, stats = self.apply_title_filter(jobs)
        await self.save_results(matched_jobs)
        
        return matched_jobs
