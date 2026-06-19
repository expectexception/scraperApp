import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class FlyingGroupScraper(BaseScraper):
    """
    Scraper for FLYINGGROUP
    URL: https://www.flyinggroup.aero/jobs/
    """
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="flyinggroup", db_manager=db_manager)
        self.base_url = "https://www.flyinggroup.aero/jobs/"
        self.company_name = "FLYINGGROUP"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)

                # Extract job links
                links = await page.evaluate('''() => {
                    let items = Array.from(document.querySelectorAll('a'));
                    return items.map(a => ({href: a.href, text: a.innerText.trim()}))
                        .filter(a => a.href && a.href.includes('/20') && a.text.length > 5 && !a.href.includes('category') && !a.href.includes('tag'));
                }''')

                seen_urls = set()
                job_links = []
                for link in links:
                    if link['href'] not in seen_urls:
                        seen_urls.add(link['href'])
                        job_links.append(link)

                logger.info(f"[{self.site_key}] Found {len(job_links)} job links")

                for job_data in job_links:
                    if self.max_jobs and len(jobs) >= self.max_jobs: break
                    try:
                        url = job_data["href"]
                        title = job_data["text"]
                        
                        # In wordpress standard article lists, the title often has the date prepended.
                        if "\\n" in title:
                            title = title.split("\\n")[-1].strip()

                        job_id = f"flyinggroup_{abs(hash(url)) % 10000000}"
                        jobs.append({
                            "job_id": job_id,
                            "title": title,
                            "company": self.company_name,
                            "source": self.site_key,
                            "url": url,
                            "apply_url": url,
                            "location": "Antwerp, Belgium", # Default base for Flyinggroup, might refine
                        })
                    except Exception as e:
                        continue
            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
            finally:
                await context.close()
                await browser.close()
        return jobs

    async def fetch_job_descriptions(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not jobs: return []
        logger.info(f"[{self.site_key}] Fetching details for {len(jobs)} jobs...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            for job in jobs:
                try:
                    page, context = await self.setup_stealth_page(browser)
                    await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
                    
                    desc = await self.extract_description_from_page(page)
                    job["description"] = desc

                    # Attempt to refine location if mentioned
                    text_lower = desc.lower()
                    if "luxembourg" in text_lower:
                        job["location"] = "Luxembourg"
                    elif "paris" in text_lower:
                        job["location"] = "Paris, France"
                    elif "geneva" in text_lower:
                        job["location"] = "Geneva, Switzerland"
                        
                    job["posted_date"] = await self.extract_posted_date_from_page(page)
                    
                except Exception as e:
                    logger.warning(f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}")
                finally:
                    await context.close()
                await asyncio.sleep(1)
            await browser.close()
            
        return jobs

    async def run(self):
        self.print_header()
        jobs_raw = await self.fetch_jobs()
        jobs = [get_job_dict(**job) for job in jobs_raw]
        if not jobs: return []
        if self.use_filter and self.filter_manager:
            jobs, _, _ = self.apply_title_filter(jobs)
            if not jobs: return []
        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs: return []
        jobs = await self.fetch_job_descriptions(jobs)
        await self.save_results(jobs)
        return jobs
