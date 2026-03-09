import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright
import re

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class AbsjetsScraper(BaseScraper):
    """
    Scraper for ABS Jets Careers
    URL: https://www.absjets.com/careers-109
    """
    
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key='absjets', db_manager=db_manager)
        self.base_url = "https://www.absjets.com/careers-109"
        self.domain = "https://www.absjets.com"
        self.company_name = "ABS Jets"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            try:
                page = await context.new_page()
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                
                try:
                    await page.goto(self.base_url, wait_until='networkidle', timeout=60000)
                except Exception as e:
                    logger.error(f"[{self.site_key}] Navigation failed: {e}")
                    return []
                
                await page.wait_for_timeout(3000)
                
                # Fetch all job links
                # The URLs contain "?r=detail&id="
                links = await page.locator('a[href*="?r=detail&id="]').all()
                logger.info(f"[{self.site_key}] Found {len(links)} potential job rows")
                
                seen_urls = set()
                job_urls = []
                for link in links:
                    href = await link.get_attribute('href')
                    if href:
                        full_link = f"{self.domain}{href}" if href.startswith('/') else href
                        if full_link not in seen_urls:
                            seen_urls.add(full_link)
                            job_urls.append(full_link)
                
                for i, url in enumerate(job_urls):
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    try:
                        logger.info(f"[{self.site_key}] Fetching details for: {url}")
                        detail_page = await context.new_page()
                        await detail_page.goto(url, wait_until='networkidle', timeout=30000)
                        
                        await detail_page.wait_for_timeout(2000)
                        
                        content = await detail_page.inner_text('body')
                        
                        title = ""
                        title_locs = await detail_page.locator('h1, h2').all()
                        if title_locs:
                            for t_loc in title_locs:
                                t_text = await t_loc.inner_text()
                                if t_text and len(t_text.strip()) > 3:
                                    title = t_text
                                    break
                        
                        if not title:
                            title = "Unknown Title"
                            
                        title = title.strip()
                            
                        description = ""
                        desc_loc = detail_page.locator('.teamio-detail-content, .job-description, .detail-content, .content, main')
                        if await desc_loc.first.is_visible():
                            description = await desc_loc.first.inner_html()
                        else:
                            description = await self.extract_description_from_page(detail_page)

                        location = "Unknown Location"
                        m_loc = re.search(r'(Praha|Bratislava|Brno|Ostrava).*', content, re.IGNORECASE)
                        if m_loc:
                            location = m_loc.group(0).strip()
                            
                        posted_date = await self.extract_posted_date_from_page(detail_page)

                        job_id = None
                        match = re.search(r'id=(\d+)', url)
                        if match:
                            job_id = match.group(1)
                        if not job_id:
                            job_id = f"abs_{i}"

                        job = get_job_dict(
                            job_id=f"absjets_{job_id}",
                            title=title,
                            company=self.company_name,
                            location=location,
                            url=url,
                            source_url=url,
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
                await browser.close()
                
        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        jobs = [j for j in jobs if j is not None]
        await self.save_results(jobs)
        return jobs
