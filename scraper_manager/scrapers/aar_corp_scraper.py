import asyncio
import logging
import re
from datetime import datetime
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class AARCorpScraper(BaseScraper):
    """
    Scraper for AAR Corp
    URL: https://aarcorp.taleo.net/careersection/2/jobsearch.ftl?lang=en
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='aar_corp', db_manager=db_manager)
        self.base_url = "https://aarcorp.taleo.net/careersection/2/jobsearch.ftl?lang=en"
        self.company_name = "AAR Corp"

    async def fetch_jobs(self) -> list:
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until='domcontentloaded', timeout=60000)
                await page.wait_for_timeout(5000)
                
                # Check for "View All Jobs" or Reset Filters
                try:
                    # Taleo often has a 'Clear' button or 'View All Jobs' link
                    clear_btn = page.locator('#clearButton').first
                    if await clear_btn.is_visible():
                        logger.info(f"[{self.site_key}] Clicking clearButton to reset filters...")
                        await clear_btn.click()
                        await page.wait_for_timeout(5000)
                    else:
                        view_all = page.locator('#viewAllJobsLink').first
                        if await view_all.is_visible():
                            logger.info(f"[{self.site_key}] Clicking viewAllJobsLink...")
                        await view_all.click()
                        await page.wait_for_timeout(5000)
                    
                    # Switch to Single-line view to see posted dates in the table
                    # In Taleo, the link text often indicates the target view.
                    # If the link says 'Single-line', we should click it. If it says 'Multi-line', we are already in Single-line.
                    switch_view = page.locator('#listFormatSwitch').first
                    if await switch_view.is_visible():
                        view_text = await switch_view.inner_text()
                        if 'Single-line' in view_text:
                            logger.info(f"[{self.site_key}] Switching to Single-line view (found 'Single-line' in link text)...")
                            await switch_view.click()
                            await page.wait_for_timeout(5000)
                        else:
                            logger.info(f"[{self.site_key}] Already in Single-line view (link text is '{view_text}').")
                except Exception as e:
                    logger.debug(f"[{self.site_key}] No clear/view-all/switch-view button found or clickable: {e}")

                page_count = 1
                while True:
                    if self.max_pages and page_count > self.max_pages:
                        break
                        
                    logger.info(f"[{self.site_key}] Processing page {page_count}...")
                    
                    # Extract jobs from the table using a more resilient approach
                    # Find all table rows that contain a job link
                    job_rows = await page.evaluate('''() => {
                        let rows = Array.from(document.querySelectorAll('tr'));
                        return rows.filter(tr => tr.querySelector('a[id^="job"]')).map(tr => tr.id || tr.className);
                    }''')
                    
                    if not job_rows:
                        logger.warning(f"[{self.site_key}] No job rows found on page {page_count}")
                        # Final attempt: look for ANY links with 'jobdetail.ftl'
                        job_rows = await page.evaluate('''() => {
                            return Array.from(document.querySelectorAll('a[href*="jobdetail.ftl"]'))
                                .map(a => a.id || a.parentElement.id);
                        }''')

                    if not job_rows:
                        logger.warning(f"[{self.site_key}] Still no job rows found on page {page_count}")
                        await page.screenshot(path="no_jobs_debug.png")
                        break

                    logger.info(f"[{self.site_key}] Found {len(job_rows)} job rows on page {page_count}")
                    
                    # Since we can't easily pass element handles from evaluate back to python for nested queries,
                    # let's just extract EVERYTHING in one go via evaluate.
                    page_jobs_data = await page.evaluate('''() => {
                        let jobs = [];
                        // Find all rows in the jobs table specifically
                        let table = document.querySelector('table#jobs');
                        if (!table) return [];
                        
                        let rows = Array.from(table.rows).filter(tr => tr.querySelector('a[href*="jobdetail.ftl"]'));
                        
                        for (let row of rows) {
                            let link = row.querySelector('a[href*="jobdetail.ftl"]');
                            if (!link) continue;
                            
                            let title = link.innerText.trim();
                            let url = link.href;
                            
                            // Requisition number often in the title
                            // or in another cell.
                            
                            // Try to find posted date in the 3rd column
                            let cells = Array.from(row.cells);
                            let dateText = "";
                            if (cells.length >= 3) {
                                dateText = cells[2].innerText.trim();
                            }
                            
                            // Fallback for date search in any cell
                            if (!dateText || !/\\d/.test(dateText)) {
                                for(let cell of cells) {
                                    let t = cell.innerText;
                                    if(/\\d{1,2}[/-]\\d{1,2}[/-]\\d{4}|[A-Z][a-z]{2}\\s+\\d{1,2},?\\s+\\d{4}/.test(t)) {
                                        dateText = t.trim();
                                        break;
                                    }
                                }
                            }
                            
                            jobs.push({title, url, dateText});
                        }
                        return jobs;
                    }''')

                    # Visit each job detail page
                    for job_data in page_jobs_data:
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break
                            
                        url = job_data['url']
                        title = job_data['title']
                        
                        if not self.is_job_link(title, url):
                            continue
                            
                        if not self.should_process_job(title):
                            continue

                        if await self.is_url_already_scraped(url):
                            continue

                        try:
                            logger.info(f"[{self.site_key}] Fetching details for: {url}")
                            detail_page = await context.new_page()
                            await detail_page.goto(url, wait_until='domcontentloaded', timeout=30000)
                            await detail_page.wait_for_timeout(2000)
                            
                            description = await self.extract_description_from_page(detail_page)
                            # Specifically look for Taleo description ID
                            taleo_desc = await detail_page.query_selector('#requisitionDescriptionInterface')
                            if taleo_desc:
                                description = await taleo_desc.inner_text()

                            # Extract location
                            location = "USA" # Default
                            loc_text = await detail_page.evaluate('''() => {
                                let elements = Array.from(document.querySelectorAll('.editableschematicfield label, .ftlrow label'));
                                for(let el of elements) {
                                    if(el.innerText.includes('Primary Location') || el.innerText.includes('Location')) {
                                        return el.nextElementSibling ? el.nextElementSibling.innerText.trim() : "";
                                    }
                                }
                                return "";
                            }''')
                            if loc_text:
                                location = loc_text

                            # Job ID from URL or requisition number
                            job_id_match = re.search(r'job=(\d+)', url)
                            job_id = f"aar_{job_id_match.group(1)}" if job_id_match else f"aar_{hash(url)}"

                            posted_date = self.parse_posted_date(job_data['dateText']) if job_data.get('dateText') else None

                            job = get_job_dict(
                                job_id=job_id,
                                title=title,
                                company=self.company_name,
                                location=location,
                                url=url,
                                source_url=self.base_url,
                                description=description,
                                apply_url=url,
                                posted_date=posted_date,
                                source=self.site_key
                            )
                            
                            jobs.append(job)
                            await detail_page.close()
                            await self.random_delay(1, 2)
                            
                        except Exception as e:
                            logger.error(f"[{self.site_key}] Error fetching job detail ({url}): {e}")
                            continue

                    # Pagination
                    try:
                        next_btn = page.locator('#next').first
                        if await next_btn.is_visible() and await next_btn.is_enabled():
                            logger.info(f"[{self.site_key}] Clicking Next button...")
                            await next_btn.click()
                            await page.wait_for_timeout(5000)
                            page_count += 1
                        else:
                            logger.info(f"[{self.site_key}] No more pages found.")
                            break
                    except Exception as e:
                        logger.error(f"[{self.site_key}] Error navigating to next page: {e}")
                        break
                        
            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
            finally:
                await context.close()
                await browser.close()
                
        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        jobs = [j for j in jobs if j is not None]
        
        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs

    def is_job_link(self, title, url):
        """Helper to validate if a link is actually a job"""
        if not title or len(title) < 3:
            return False
        if "jobdetail.ftl" not in url:
            return False
        return True
