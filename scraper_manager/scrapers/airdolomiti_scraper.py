import asyncio
import logging
import re
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class AirDolomitiScraper(BaseScraper):
    """
    Scraper for Air Dolomiti.
    URL: https://airdolomiti.altamiraweb.com/
    Uses Altamira ATS structure.
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='airdolomiti', db_manager=db_manager)
        self.base_url = "https://airdolomiti.altamiraweb.com/default"
        self.company_name = "Air Dolomiti"

    async def fetch_jobs(self) -> list:
        logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                try:
                    await page.goto(self.base_url, wait_until='networkidle', timeout=60000)
                except Exception as e:
                    logger.error(f"[{self.site_key}] Navigation failed: {e}")
                    return []
                
                # Fetch job links
                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a.GRID_DAT_COMMAND'))
                        .map(a => ({t: a.innerText.trim(), h: a.href}))
                }''')
                
                logger.info(f"[{self.site_key}] Found {len(links)} potential job links")
                
                seen_urls = set()
                initial_jobs = []
                for link in links:
                    href = link['h']
                    title = link['t']
                    if href and href not in seen_urls and self.is_job_link(title, href):
                        skip_words = ['home', 'news', 'faq', 'cookie', 'login', 'impressum', 'privacy', 'about', 'search', 'results']
                        if any(kw == title.lower() for kw in skip_words) or title.lower() in skip_words:
                            continue
                        seen_urls.add(href)
                        initial_jobs.append({'title': title, 'url': href})
                
                logger.info(f"[{self.site_key}] Found {len(initial_jobs)} potential jobs. Applying pre-filter...")
                
                # PRE-FILTER: Filter by title first to skip irrelevant roles COMPLETELY
                matched_initial, _, _ = self.apply_title_filter(initial_jobs)
                
                logger.info(f"[{self.site_key}] {len(matched_initial)} jobs passed pre-filtering. Fetching details...")

                for i, j_initial in enumerate(matched_initial):
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    url = j_initial['url']
                    title = j_initial['title']
                        
                    try:
                        logger.info(f"[{self.site_key}] Fetching details for: {url}")
                        detail_page = await context.new_page()
                        # Increased timeout for stability
                        await detail_page.goto(url, wait_until='load', timeout=60000)
                        await detail_page.wait_for_timeout(2000)
                        
                        real_title = title
                        h1 = detail_page.locator('h1').first
                        if await h1.is_visible():
                            extracted = await h1.inner_text()
                            if len(extracted) > 5:
                                real_title = extracted

                        description = ""
                        for loc in ['.jobdescription', '.job-description', 'main', '.annuncio_content', '#annuncio']:
                            elem = detail_page.locator(loc).first
                            if await elem.is_visible():
                                description = await elem.inner_html()
                                break
                                
                        if not description:
                            description = await self.extract_description_from_page(detail_page)

                        location = "Italy"
                        for loc in ['.jobGeoLocation', '.location', '.job-location']:
                            elem = detail_page.locator(loc).first
                            if await elem.is_visible():
                                loc_text = await elem.inner_text()
                                if loc_text: location = loc_text.strip()
                                break
                                
                        posted_date = await self.extract_posted_date_from_page(detail_page)
                        
                        job_id = f"airdolomiti_{i+1}"
                        match = re.search(r'-(\d+)\.htm', url)
                        if match and match.group(1):
                            job_id = f"airdolomiti_{match.group(1)}"

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
                        logger.error(f"[{self.site_key}] Error parsing job {i} ({url}): {e}")
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
        await self.save_results(jobs)
        return jobs
