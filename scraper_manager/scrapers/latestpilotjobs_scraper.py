import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from datetime import datetime, timedelta
import re

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class LatestPilotJobsScraper(BaseScraper):
    """
    Scraper for LatestPilotJobs.com Ground Crew Jobs
    URL: https://www.latestpilotjobs.com/jobs/category/id/ground_crew_jobs.html
    """
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="latestpilotjobs", db_manager=db_manager)
        self.base_url = "https://www.latestpilotjobs.com/jobs/category/id/ground_crew_jobs.html"
        self.company_name = "Latest Pilot Jobs" # Fallback, usually we extract the actual company

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(3)

                # Attempt to get pagination or just collect all job links
                # The jobs are typically in list items
                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll("a")).map(a => ({
                        href: a.href,
                        text: a.innerText || a.textContent
                    }));
                }''')
                
                job_links = []
                for link in links:
                    href = link.get("href", "")
                    text = link.get("text", "").strip()
                    if not href or len(text) < 3: continue
                    
                    if "/jobs/view/id/" in href.lower() and text.lower() not in ["view details", "read more"]:
                        if not any(j["url"] == href for j in job_links):
                            job_links.append({
                                "url": href,
                                "title": text
                            })
                
                logger.info(f"[{self.site_key}] Found {len(job_links)} potential job links")

                for job_data in job_links:
                    if self.max_jobs and len(jobs) >= self.max_jobs: break
                    try:
                        job_url = job_data["url"]
                        title = job_data["title"]
                        
                        job_id = f"latestpilotjobs_{abs(hash(job_url)) % 10000000}"
                        jobs.append({
                            "job_id": job_id,
                            "title": title,
                            "company": "Unknown Airline", # Will refine in detail page
                            "source": self.site_key,
                            "url": job_url,
                            "apply_url": job_url,
                            "location": "Unknown", 
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
                    
                    # Extract Company and Location
                    meta_info = await page.evaluate('''() => {
                        let text = document.body.innerText;
                        let company = "";
                        let location = "";
                        let date = "";
                        
                        let items = document.querySelectorAll('.detail-view tr, .job-details p, td');
                        items.forEach(el => {
                            let t = el.innerText || "";
                            if(t.includes("Company:")) company = t.split("Company:")[1].trim();
                            else if(t.includes("Employer:")) company = t.split("Employer:")[1].trim();
                            
                            if(t.includes("Location:")) location = t.split("Location:")[1].trim();
                            if(t.includes("Date:")) date = t.split("Date:")[1].trim();
                        });
                        return { company, location, date };
                    }''')
                    
                    if meta_info.get("company"):
                        job["company"] = meta_info["company"].split('\n')[0].strip()
                    if meta_info.get("location"):
                        job["location"] = meta_info["location"].split('\n')[0].strip()
                        
                    # Extract exact apply URL
                    apply_link = await page.evaluate('''() => {
                        let btn = document.querySelector('a[href*="apply"], a.btn-apply, a:contains("Apply")');
                        if(btn && btn.href && !btn.href.includes("latestpilotjobs")) return btn.href;
                        
                        // Check all links to see if there's an external one that looks like an application
                        let links = Array.from(document.querySelectorAll("a"));
                        for(let a of links) {
                            let t = (a.innerText || "").toLowerCase();
                            if ((t.includes("apply") || t.includes("here")) && !a.href.includes("latestpilotjobs.com")) {
                                return a.href;
                            }
                        }
                        return "";
                    }''')
                    
                    if apply_link:
                        job["apply_url"] = apply_link
                        logger.info(f"[{self.site_key}] Found external apply URL: {apply_link}")
                        
                    # Description
                    desc = ""
                    for sel in [".job-content", ".detail-view", ".job-description", "main", ".content"]:
                        el = await page.query_selector(sel)
                        if el:
                            text = await el.inner_text()
                            if len(text) > 100:
                                desc = text.strip()
                                break
                    if not desc:
                        desc = await self.extract_description_from_page(page)
                    job["description"] = desc
                    # Backfill location from the original posting when missing.
                    if not job.get("location") or job.get("location") == "Unknown":
                        _loc = await self.extract_location_from_page(page)
                        if _loc:
                            job["location"] = _loc
                    
                except Exception as e:
                    logger.warning(f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}")
                finally:
                    await context.close()
                await asyncio.sleep(1)
            await browser.close()
            
        # Validity Check
        valid_jobs = []
        for job in jobs:
            # Drop jobs that look clearly invalid or expired if explicitly mentioned
            desc = job.get("description", "").lower()
            if "expired" in desc[:200] or "filled" in desc[:200]:
                logger.info(f"[{self.site_key}] Job {job['title']} appears expired, dropping.")
                continue
            if len(desc) < 50:
                logger.info(f"[{self.site_key}] Job {job['title']} has too short description, dropping.")
                continue
            valid_jobs.append(job)
            
        return valid_jobs

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
