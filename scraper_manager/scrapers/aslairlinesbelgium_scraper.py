import asyncio
import logging
from datetime import datetime
from playwright.async_api import async_playwright
import re

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class ASLAirlinesBelgiumScraper(BaseScraper):
    """
    Scraper for ASL Airlines Belgium
    URL: https://aslairlines.be/asljobs/
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='aslairlinesbelgium', db_manager=db_manager)
        self.base_url = "https://cezanneondemand.intervieweb.it/aslaviationgroup/en/career"
        self.company_name = "ASL Airlines Belgium"

    async def fetch_jobs(self) -> list:
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                
                try:
                    await page.goto(self.base_url, wait_until='domcontentloaded', timeout=45000)
                    await self.random_delay(2, 4)
                except Exception as e:
                    logger.error(f"[{self.site_key}] Navigation failed: {e}")
                    return []
                
                # Intervieweb job links
                job_links = await page.evaluate('''() => {
                    let results = [];
                    let cards = document.querySelectorAll('.vacancy__render, .panel.vacancy, .card');
                    if (cards.length === 0) {
                        cards = document.querySelectorAll('#vacancyList .row, #vacancies .row');
                    }
                    cards.forEach(card => {
                        let a = card.querySelector('a.btn-primary') || card.querySelector('a');
                        let titleElem = card.querySelector('.vacancy__title') || card.querySelector('h3');
                        let locElem = card.querySelector('.fa-map-marker-alt');
                        
                        let title = titleElem ? titleElem.innerText.trim() : '';
                        let loc = locElem && locElem.nextSibling ? locElem.nextSibling.textContent.trim() : '';
                        if (!loc && card.innerText) {
                            let parts = card.innerText.split('\\n');
                            loc = parts.find(p => p.includes('Belgium') || p.includes('Liege') || p.includes('Hollogne') || p.includes('Brussels')) || 'Belgium';
                        }
                        
                        if (a && a.href && title) {
                            results.push({t: title, h: a.href, loc: loc});
                        }
                    });
                    
                    if (results.length === 0) {
                        // Fallback if structure is different
                        let links = document.querySelectorAll('#vacancyList a, #vacancies a');
                        links.forEach(a => {
                            let text = a.innerText.trim();
                            if (text.length > 5 && text.toUpperCase() !== 'APPLY') {
                                results.push({t: text, h: a.href, loc: 'Unknown'});
                            }
                        });
                    }
                    return results;
                }''')
                
                logger.info(f"[{self.site_key}] Found {len(job_links)} total job links")
                for link in job_links:
                    print(f"DEBUG ALSL: {link['t']} -> {link['loc']}")
                
                seen_urls = set()
                job_urls = []
                for link in job_links:
                    href = link['h']
                    title = link['t']
                    loc = link.get('loc', '')
                    if href and href not in seen_urls and ('Belgium' in loc or 'Hollogne' in loc or 'Liege' in loc or 'Brussels' in loc):
                        seen_urls.add(href)
                        job_urls.append((href, title))
                
                for i, (url, title) in enumerate(job_urls):
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    try:
                        logger.info(f"[{self.site_key}] Fetching details for: {url}")
                        detail_page = await context.new_page()
                        await detail_page.goto(url, wait_until='domcontentloaded', timeout=30000)
                        
                        await detail_page.wait_for_timeout(2000)
                        description = ""
                        desc_elements = await detail_page.query_selector_all('.body__text')
                        if desc_elements:
                            for el in desc_elements:
                                description += await el.inner_html() + "<br><br>"
                                
                        if not description:
                            desc_loc = detail_page.locator('main, .elementor-widget-container, .entry-content, article')
                            if await desc_loc.first.is_visible():
                                description = await desc_loc.first.inner_html()
                                
                        if not description:
                            description = await self.extract_description_from_page(detail_page)

                        location = "Liege/Belgium"
                        loc_elem = await detail_page.query_selector('span.subtitle__informations[title="Location"]')
                        if loc_elem:
                            loc_text = await loc_elem.inner_text()
                            if loc_text: location = loc_text.strip()
                        
                        posted_date = await self.extract_posted_date_from_page(detail_page)

                        job_id = None
                        match = re.search(r'-(\d+)', url)
                        if match: job_id = match.group(1)
                        if not job_id: job_id = url.strip('/').split('/')[-1]

                        job = get_job_dict(
                            job_id=f"aslbe_{job_id}",
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
                await context.close()
                await browser.close()
                
        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        jobs = [j for j in jobs if j is not None]
        await self.save_results(jobs)
        return jobs
