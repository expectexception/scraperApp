import asyncio
import logging
from datetime import datetime
from playwright.async_api import async_playwright
import re

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class AirMaltaScraper(BaseScraper):
    """
    Scraper for Air Malta (KM Malta Airlines) Careers
    URL: https://kmmaltairlines.com/en/careers
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='airmalta', db_manager=db_manager)
        self.base_url = "https://kmmaltairlines.com/en/careers"
        self.domain = "https://kmmaltairlines.com"
        self.company_name = "Air Malta"

    async def fetch_jobs(self) -> list:
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
                    await page.goto(self.base_url, wait_until='domcontentloaded', timeout=45000)
                except Exception as e:
                    logger.error(f"[{self.site_key}] Navigation failed: {e}")
                    return []
                
                await page.wait_for_timeout(3000)
                
                # KM Malta Links
                links = await page.evaluate('''() => {
                    let results = [];
                    // Extract from standard cards
                    let cards = document.querySelectorAll('.block-item');
                    cards.forEach(card => {
                        let a = card.querySelector('a.block-item-button');
                        let title = card.querySelector('.block-item-title');
                        if (a && title && a.href) {
                            results.push({t: title.innerText.trim(), h: a.href});
                        }
                    });
                    
                    // Extract from hero job
                    let heroLink = document.querySelector('.text-wrapper a.btn-primary');
                    let heroTitle = document.querySelector('.text-wrapper h1');
                    if (heroLink && heroTitle && heroLink.href) {
                        results.push({t: heroTitle.innerText.trim(), h: heroLink.href});
                    }
                    
                    return results;
                }''')
                
                logger.info(f"[{self.site_key}] Found {len(links)} potential job links")
                
                seen_urls = set()
                job_urls = []
                for link in links:
                    href = link['h']
                    title = link['t']
                    if href and href not in seen_urls and self.is_job_link(title, href):
                        if not self.should_process_job(title):
                            continue
                        seen_urls.add(href)
                        job_urls.append((href, title))
                
                for i, (url, title) in enumerate(job_urls):
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    try:
                        logger.info(f"[{self.site_key}] Fetching details for: {url}")
                        detail_page = await context.new_page()
                        await detail_page.goto(url, wait_until='domcontentloaded', timeout=45000)
                        
                        await detail_page.wait_for_timeout(2000)
                        
                        # Use the last part of URL as title fallback
                        title = url.split('/')[-1].replace('-', ' ').replace('_', ' ')
                        
                        title_loc = detail_page.locator('h1, .hero-title, .job-title')
                        if await title_loc.first.is_visible():
                            extracted_title = await title_loc.first.inner_text()
                            if extracted_title and len(extracted_title) > 3:
                                title = extracted_title
                            
                        title = title.strip()
                            
                        description = ""
                        desc_loc = detail_page.locator('.article-content, .job-description, .content, main')
                        if await desc_loc.first.is_visible():
                            description = await desc_loc.first.inner_html()
                        else:
                            description = await self.extract_description_from_page(detail_page)

                        location = "Malta" # KM Malta jobs are usually based in Malta
                        loc_elem = detail_page.locator('section.striped-table tr:nth-child(2) td:last-child')
                        if await loc_elem.first.is_visible():
                            loc_text = await loc_elem.first.inner_text()
                            if loc_text: location = loc_text.strip()
                        
                        posted_date = await self.extract_posted_date_from_page(detail_page)

                        job_id = url.split('/')[-1] if '/' in url else f"airmalta_{i}"
                        
                        job = get_job_dict(
                            job_id=f"airmalta_{job_id}",
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
        
        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
