import asyncio
import logging
import re
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class NorwegianScraper(BaseScraper):
    """
    Scraper for Norwegian Air Shuttle.
    URL: https://careers.norwegian.com/viewalljobs/
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='norwegian', db_manager=db_manager)
        self.base_url = "https://careers.norwegian.com/search/"
        self.company_name = "Norwegian Air Shuttle"

    async def fetch_jobs(self) -> list:
        logger.info(f"[{self.site_key}] Navigating to {self.base_url} (Headless={self.headless})...")
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                await page.goto(self.base_url, wait_until='networkidle', timeout=60000)
                await self.simulate_human_behavior(page)
                
                # Handle cookie banner
                try:
                    cookie_btn = page.locator('#cookie-acknowledge, text="Accept All", text="Allow All"').first
                    if await cookie_btn.is_visible():
                        await cookie_btn.click()
                        await page.wait_for_timeout(1000)
                except:
                    pass

                # SuccessFactors interaction: Click search to reveal jobs
                try:
                    search_btn = page.locator('button:has-text("Search Jobs")').first
                    if await search_btn.is_visible():
                        await search_btn.click()
                        await page.wait_for_selector('a.jobTitle-link', timeout=20000)
                    else:
                        # Sometimes it loads automatically, but wait for indicator
                        await page.wait_for_selector('a.jobTitle-link', timeout=10000)
                except:
                    logger.warning(f"[{self.site_key}] Job list did not appear after interaction.")

                # Fetch job links from the SuccessFactors list
                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a.jobTitle-link'))
                        .map(a => ({t: a.innerText.trim(), h: a.href}))
                }''')
                
                logger.info(f"[{self.site_key}] Found {len(links)} potential job links")
                
                seen_urls = set()
                job_urls = []
                for link in links:
                    href = link['h']
                    title = link['t']
                    if href and href not in seen_urls and self.is_job_link(title, href):
                        seen_urls.add(href)
                        job_urls.append((href, title))
                
                for i, (url, title) in enumerate(job_urls):
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    try:
                        if not self.should_process_job(title):
                            continue

                        if await self.is_url_already_scraped(url):
                            continue

                        logger.info(f"[{self.site_key}] Fetching details for: {url}")
                        detail_page = await context.new_page()
                        await detail_page.goto(url, wait_until='domcontentloaded', timeout=30000)
                        await detail_page.wait_for_timeout(2000)
                        
                        real_title = title
                        h1 = detail_page.locator('h1').first
                        if await h1.is_visible():
                            extracted = await h1.inner_text()
                            if len(extracted) > 5:
                                real_title = extracted

                        description = ""
                        # SuccessFactors often has job description in a specific div
                        for loc in ['.jobdescription', '.content', '.jo-job-description', 'main']:
                            elem = detail_page.locator(loc).first
                            if await elem.is_visible():
                                description = await elem.inner_html()
                                break
                                
                        if not description:
                            description = await self.extract_description_from_page(detail_page)

                        # SuccessFactors location extraction
                        location = "Norway"
                        try:
                            loc_val = await detail_page.evaluate('''() => {
                                let label = Array.from(document.querySelectorAll('span')).find(s => s.innerText.includes('Location'));
                                if(label && label.nextElementSibling) return label.nextElementSibling.innerText.trim();
                                return "";
                            }''')
                            if loc_val: location = loc_val
                        except:
                            pass
                                
                        posted_date = await self.extract_posted_date_from_page(detail_page)
                        
                        job_id = f"norwegian_{hash(url)}"
                        match = re.search(r'job-id=(\d+)', url)
                        if match:
                            job_id = f"norwegian_{match.group(1)}"

                        job = get_job_dict(
                            job_id=job_id,
                            title=real_title,
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
                        
                    except Exception as e:
                        logger.error(f"[{self.site_key}] Error parsing job detail ({url}): {e}")
                        continue
                        
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
