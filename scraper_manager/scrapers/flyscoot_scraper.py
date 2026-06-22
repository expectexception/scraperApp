import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class FlyScootScraper(BaseScraper):
    """
    Scraper for Scoot (FlyScoot)
    URL: https://careers.flyscoot.com/jobs-board
    """
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="flyscoot", db_manager=db_manager)
        self.base_url = "https://careers.flyscoot.com/jobs-board?department=flight%20operations"
        self.company_name = "Scoot"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(5000)
                
                try:
                    await page.wait_for_selector(".job-card", timeout=15000)
                except Exception as e:
                    logger.warning(f"[{self.site_key}] Timeout waiting for .job-card: {e}")
                    return []

                cards = await page.query_selector_all(".job-card")
                logger.info(f"[{self.site_key}] Found {len(cards)} job cards.")

                for card in cards:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                    try:
                        title_el = await card.query_selector(".job-title")
                        if not title_el:
                            continue
                        title = await title_el.inner_text()
                        title = title.strip()
                        
                        share_icon = await card.query_selector('[id^="share-icon-"]')
                        ref_id = ""
                        if share_icon:
                            share_id = await share_icon.get_attribute("id")
                            ref_id = share_id.replace("share-icon-", "")
                        
                        if not ref_id:
                            continue
                            
                        job_url = f"https://careers.flyscoot.com/job-detail/{ref_id}"
                        
                        # Get locations from tags
                        tag_els = await card.query_selector_all(".job-tag")
                        location = "Singapore"
                        tags = []
                        for t in tag_els:
                            t_text = await t.inner_text()
                            tags.append(t_text.strip())
                            if "HQ" in t_text or "SINGAPORE" in t_text.upper():
                                location = "Singapore"
                                
                        # Date
                        posted_date = None
                        posted_el = await card.query_selector(".job-start-date")
                        if posted_el:
                            posted_text = await posted_el.inner_text()
                            posted_date = self.parse_posted_date(posted_text)

                        jobs.append({
                            "job_id": f"flyscoot_{ref_id}",
                            "title": title,
                            "company": self.company_name,
                            "source": self.site_key,
                            "url": job_url,
                            "apply_url": job_url,
                            "location": location,
                            "posted_date": posted_date,
                        })
                    except Exception as e:
                        logger.error(f"[{self.site_key}] Error parsing card: {e}")
                        continue
            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
            finally:
                await context.close()
                await browser.close()
        return jobs

    async def fetch_job_descriptions(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not jobs: return []
        logger.info(f"[{self.site_key}] Fetching descriptions for {len(jobs)} matched jobs...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            for job in jobs:
                try:
                    page, context = await self.setup_stealth_page(browser)
                    await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
                    desc = ""
                    selectors = [".job-detail", ".job-description-container", ".job-description", ".content", "main"]
                    for sel in selectors:
                        el = await page.query_selector(sel)
                        if el:
                            text = await el.inner_text()
                            if len(text) > 100:
                                desc = text.strip()
                                break
                    if not desc:
                        desc = await self.extract_description_from_page(page)
                    job["description"] = desc
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
