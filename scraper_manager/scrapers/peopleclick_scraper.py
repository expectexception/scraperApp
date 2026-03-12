"""
PeopleClick / Cargolux Careers Scraper
Extracts aviation jobs from careers.peopleclick.eu.com (Cargolux client)

Notes:
- Uses direct JSON API discovered via browser inspection for high reliability.
- Extracts job_id, title, company, url, location, posted_date, and full description in one pass.
"""

import asyncio
import logging
import re
import json
from datetime import datetime
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Page

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class CargoluxPeopleClickScraper(BaseScraper):
    """Scraper for Cargolux Careers (PeopleClick)
    """

    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key='cargolux', db_manager=db_manager)
        self.site_config = config.get('sites', {}).get('cargolux', {})
        self.base_url = "https://careers.peopleclick.eu.com"
        self.jobs_url = "https://careers.peopleclick.eu.com/careerscp/client_cargolux/external/results/searchResult.html"
        self.api_url = "https://careers.peopleclick.eu.com/careerscp/api/client_cargolux/external/site/getJobs"
        self.company_name = "Cargolux"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """Fetch jobs from PeopleClick using the internal JSON API"""
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                # 1. Navigate to search page and trigger search to establish a valid session
                logger.info(f"[{self.site_key}] Establishing session at {self.jobs_url}")
                await page.goto(self.jobs_url, wait_until='networkidle', timeout=60000)
                await asyncio.sleep(5)
                
                # Click the search button if present to initialize the results
                search_btn = await page.query_selector('#sp-searchButton')
                if search_btn:
                    logger.info(f"[{self.site_key}] Clicking search button to initialize session...")
                    await search_btn.click()
                    await asyncio.sleep(5)

                # 2. Fetch job data via JSON API using page.evaluate to inherit cookies/session
                logger.info(f"[{self.site_key}] Fetching jobs from API...")
                api_response = await page.evaluate(f'''async (url) => {{
                    const resp = await fetch(url, {{
                        headers: {{
                            'Accept': 'application/json, text/plain, */*',
                            'X-Requested-With': 'XMLHttpRequest'
                        }}
                    }});
                    return resp.json();
                }}''', self.api_url)
                
                if not api_response or api_response.get('status') == 'fail':
                    logger.error(f"[{self.site_key}] API Error: {api_response.get('errorMsg', 'Unknown error')}")
                    return []
                
                job_list = api_response.get('jobList', [])
                logger.info(f"[{self.site_key}] API returned {len(job_list)} jobs")
                
                # 3. Process API data
                for raw_job in job_list:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    attr = raw_job.get('attributes', {})
                    title = attr.get('JPM_TITLE', 'Unknown Title')
                    job_post_id = raw_job.get('jobPostId')
                    
                    # Pre-filtering: check title before processing further
                    if not self.should_process_job(title):
                        continue
                        
                    # Standard URLs for PeopleClick
                    detail_url = f"{self.base_url}/careerscp/client_cargolux/external/results/jobDetails/jobDetail.html?jobPostId={job_post_id}&localeCode=en-us"
                    apply_url = f"{self.base_url}/careerscp/client_cargolux/external/registration/jobApplication.html?jobPostId={job_post_id}&localeCode=en-us"
                    
                    if await self.is_url_already_scraped(detail_url):
                        continue
                        
                    logger.info(f"[{self.site_key}] Processing: {title}")
                    
                    # Use the provided description or fallback to fetching
                    description_html = attr.get('JPM_DESCRIPTION', '')
                    description = self.clean_html(description_html) if description_html else "No description provided."
                    
                    job_data = get_job_dict(
                        job_id=f"{self.site_key}_{job_post_id}",
                        job_post_id=job_post_id,
                        title=title.strip(),
                        company=self.company_name,
                        location=attr.get('JPM_LOCATION', 'Unknown'),
                        description=description,
                        url=detail_url,
                        apply_url=apply_url,
                        source_url=self.jobs_url,
                        source=self.site_key,
                        posted_date=self.parse_posted_date(attr.get('JP_POSTEDON')) if attr.get('JP_POSTEDON') else None,
                        job_type=attr.get('FLD_JPM_CONTRACT_TYPE', 'Unknown'),
                        department=attr.get('FLD_JP_POSITION_CATEGORY', 'Unknown'),
                    )
                    
                    jobs.append(job_data)
                    
            except Exception as e:
                logger.error(f"[{self.site_key}] Error during execution: {e}")
            finally:
                await context.close()
                await browser.close()
                
        return jobs

    def clean_html(self, html_content: str) -> str:
        """Remove HTML tags and clean up whitespace from description"""
        if not html_content:
            return ""
        # Remove script and style elements
        clean_text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        # Remove tags
        clean_text = re.sub(r'<[^>]+>', ' ', clean_text)
        # Normalize whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        return clean_text

    async def run(self):
        """Main entry point"""
        self.print_header()
        jobs = await self.fetch_jobs()
        
        # Standard cleaning
        jobs = [j for j in jobs if j is not None]
        
        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
