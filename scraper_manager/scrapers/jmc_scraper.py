
import asyncio
import logging
import random
import re
from typing import List, Dict, Any
from datetime import datetime
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class JMCScraper(BaseScraper):
    """
    Scraper for JMC Aviation
    """
    
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key='jmc', db_manager=db_manager)
        self.jobs_url = "https://www.jmc-aviation.com/jobs/"
        
    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Scrape jobs from JMC Aviation
        """
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                logger.info(f"[{self.site_key}] Navigating to {self.jobs_url}")
                await page.goto(self.jobs_url, wait_until='networkidle', timeout=60000)
                
                page_count = 0
                while len(jobs) < self.max_jobs:
                    page_count += 1
                    logger.info(f"[{self.site_key}] Processing page {page_count}")
                    
                    # Wait for job listings
                    # Based on analysis, jobs are likely in a list - we'll look for the job links
                    # The pattern is usually h2 or h3 with links
                    try:
                        await page.wait_for_selector('h2 a, .job-title a', timeout=10000)
                    except Exception:
                        logger.warning(f"[{self.site_key}] No jobs found on page {page_count}")
                        break
                        
                    # Find "View vacancy & Apply" links
                    # We look for links with exact text match or containing the text
                    # Based on observation, it's a link inside the job card
                    job_links = await page.query_selector_all('a:has-text("View vacancy & Apply")')
                    
                    # Deduplicate links
                    unique_links = []
                    seen_urls = set()
                    
                    for link in job_links:
                        href = await link.get_attribute('href')
                        if href and href not in seen_urls and self.is_job_link(title, href):
                            seen_urls.add(href)
                            unique_links.append(link)
                            
                    logger.info(f"[{self.site_key}] Found {len(unique_links)} potential jobs on page")
                    
                    jobs_on_page = 0
                    for link in unique_links:
                        if len(jobs) >= self.max_jobs:
                            break
                            
                        try:
                            url = await link.get_attribute('href')
                            # Title is usually not in this link, but in a sibling or parent h2
                            # Let's try to infer title from the card
                            # Parent of link -> Card -> h2
                            card = await link.evaluate_handle('el => el.closest("div")') # Approximate, might need tuning
                            # Better approach: Navigate to detail page and get title there if missing
                            
                            # Ensure absolute URL
                            if not url.startswith('http'):
                                url = self.base_url + url
                                
                            # Check if already scraped (by URL)
                            if await self.is_url_already_scraped(url):
                                continue
                            
                            jobs_on_page += 1    
                            logger.info(f"[{self.site_key}] Processing job at: {url}")
                            
                            # Visit detail page
                            detail_page = await context.new_page()
                            try:
                                await detail_page.goto(url, wait_until='domcontentloaded', timeout=30000)
                                
                                # Extract Title from H1
                                title = "Unknown Job"
                                try:
                                    title_el = await detail_page.query_selector('h1')
                                    if title_el:
                                        title = await title_el.inner_text()
                                except Exception:
                                    pass
                                
                                # Extract Title from H1
                                title = "Unknown Job"
                                try:
                                    title_el = await detail_page.query_selector('h1')
                                    if title_el:
                                        title = await title_el.inner_text()
                                except Exception:
                                    pass
                                
                                # Extract Description - Try more specific selectors first
                                description = ""
                                try:
                                    # JMC specific container often looks like this based on common layouts
                                    # We'll try a few specific ones before fallback
                                    desc_el = await detail_page.query_selector('.job-details, .job-content, .vacancy-desc')
                                    if desc_el:
                                        description = await desc_el.inner_text()
                                    else:
                                        # Fallback to base method
                                        description = await self.extract_description_from_page(detail_page)
                                except Exception as e:
                                    logger.warning(f"[{self.site_key}] Description extraction error: {e}")
                                    description = await self.extract_description_from_page(detail_page)

                                # Extract Location
                                content_text = await detail_page.inner_text('body')
                                location = "Unknown"
                                
                                loc_match = re.search(r'Location:\s*([^\n]+)', content_text, re.IGNORECASE)
                                if loc_match:
                                    location = loc_match.group(1).strip()
                                
                                # Extract Employment Type
                                emp_type = "Contract" # Default assumption
                                type_match = re.search(r'Employment Type:\s*([^\n]+)', content_text, re.IGNORECASE)
                                if type_match:
                                    emp_type = type_match.group(1).strip()
                                    
                                # Extract Real Apply Link
                                apply_url = url # Fallback
                                try:
                                    # Look for "Apply now" link - checking multiple variations
                                    apply_btn = await detail_page.query_selector('a:has-text("Apply now"), a.apply-link, a[href*="vacancy-application"]')
                                    if apply_btn:
                                        raw_apply = await apply_btn.get_attribute('href')
                                        if raw_apply:
                                            # If relative, make absolute
                                            if not raw_apply.startswith('http'):
                                                apply_url = self.base_url + raw_apply
                                            else:
                                                apply_url = raw_apply
                                            logger.info(f"[{self.site_key}] Found Apply URL: {apply_url}")
                                except Exception as e:
                                    logger.warning(f"[{self.site_key}] Apply link extraction error: {e}")
                                    
                                job_data = {
                                    'company': 'JMC Aviation',
                                    'title': title.strip(),
                                    'location': location,
                                    'employment_type': emp_type,
                                    'description': description,
                                    'source_url': url,
                                    'apply_url': apply_url,
                                    'url': url,
                                    'posted_date': datetime.now().isoformat(),
                                    'is_active': True
                                }
                                
                                jobs.append(job_data)
                                
                            except Exception as e:
                                logger.warning(f"[{self.site_key}] Failed to process detail {url}: {e}")
                            finally:
                                await detail_page.close()
                                
                        except Exception as e:
                            logger.error(f"[{self.site_key}] Error extracting job link: {e}")
                            
                    if jobs_on_page == 0:
                        logger.info(f"[{self.site_key}] No valid new jobs found on page {page_count}")
                        break
                        
                    # Pagination
                    # Look for "Next" or page numbers
                    try:
                        next_btn = await page.query_selector('a.next, a[rel="next"], .pagination a:has-text("Next")')
                        if next_btn:
                            logger.info(f"[{self.site_key}] Navigating to next page")
                            await next_btn.click()
                            await page.wait_for_load_state('networkidle')
                            await asyncio.sleep(random.uniform(2, 4))
                        else:
                            logger.info(f"[{self.site_key}] No next button found")
                            break
                    except Exception:
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
