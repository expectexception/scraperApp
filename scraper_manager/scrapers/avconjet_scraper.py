import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class AvconJetScraper(BaseScraper):
    """
    Scraper for Avcon Jet
    URL: https://www.avconjet.at/career/#vacancies
    """
    
    CC_MAP = {
        "AT": "Austria",
        "DE": "Germany",
        "SG": "Singapore",
        "MT": "Malta",
        "CH": "Switzerland",
        "UK": "United Kingdom",
        "GB": "United Kingdom",
        "US": "United States",
        "FR": "France",
        "ES": "Spain",
        "IT": "Italy",
        "AE": "United Arab Emirates",
    }

    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="avconjet", db_manager=db_manager)
        self.base_url = "https://www.avconjet.at"
        self.jobs_url = "https://www.avconjet.at/career/#vacancies"
        self.company_name = "Avcon Jet"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        logger.info(f"[{self.site_key}] Loading jobs list using Playwright...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()
            try:
                await page.goto(self.jobs_url, wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(3000)
                
                cards = await page.evaluate('''() => {
                    let elems = Array.from(document.querySelectorAll(".career-card"));
                    return elems.map(el => {
                        let link = el.querySelector("a[href*='/job/']");
                        let titleEl = el.querySelector("h2, h3, h4, .elementor-heading-title");
                        let title = titleEl ? titleEl.innerText.trim() : "";
                        let text = el.innerText || "";
                        
                        return {
                            href: link ? link.href : null,
                            title: title,
                            text: text
                        };
                    });
                }''')
                
                logger.info(f"[{self.site_key}] Found {len(cards)} career cards on page")
                
                for c in cards:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    job_url = c["href"]
                    if not job_url:
                        continue
                        
                    title = c["title"]
                    text = c["text"]
                    
                    # Parse country code and city
                    lines = [l.strip() for l in text.split("\n") if l.strip()]
                    cc = ""
                    for i, line in enumerate(lines):
                        if line in ["full-time", "part-time", "freelance"]:
                            if i > 0:
                                cc = lines[i-1].upper()
                            break
                            
                    country_name = self.CC_MAP.get(cc, cc) if cc else ""
                    
                    # Try to extract city from title
                    city = ""
                    for sep in ["–", "-", "|"]:
                        if sep in title:
                            parts = title.split(sep)
                            if len(parts) > 1:
                                # Clean city text
                                city_candidate = parts[1].strip()
                                # Remove suffix like (F/M/X)
                                if "(" in city_candidate:
                                    city_candidate = city_candidate.split("(")[0].strip()
                                city = city_candidate
                                break
                                
                    if city and country_name:
                        location = f"{city}, {country_name}"
                    elif country_name:
                        location = country_name
                    elif city:
                        location = city
                    else:
                        location = "Unknown"
                        
                    # Normalize location
                    location = self.normalize_location(location)
                    
                    jobs.append({
                        "job_id": f"avconjet_{abs(hash(job_url)) % 10000000}",
                        "title": title,
                        "company": self.company_name,
                        "source": self.site_key,
                        "url": job_url,
                        "apply_url": job_url,
                        "location": location,
                    })
                    
            except Exception as e:
                logger.error(f"[{self.site_key}] Failed to fetch job list: {e}", exc_info=True)
            finally:
                await browser.close()
                
        return jobs

    async def fetch_job_descriptions(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not jobs:
            return []
            
        logger.info(f"[{self.site_key}] Fetching descriptions for {len(jobs)} jobs...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            
            for job in jobs:
                try:
                    page, context = await self.setup_stealth_page(browser)
                    await page.goto(job["url"], wait_until="networkidle", timeout=45000)
                    
                    body = await page.locator("body").inner_text()
                    
                    # Clean using split
                    parts = body.split("Search\n")
                    desc = parts[1] if len(parts) > 1 else body
                    
                    # Split on APPLY NOW or similar footer markers
                    for marker in ["APPLY NOW", "DOWNLOAD PDF", "HEADOFFICE"]:
                        if marker in desc:
                            desc = desc.split(marker)[0]
                            
                    job["description"] = desc.strip()
                    # Backfill location from the original posting when missing.
                    if not job.get("location") or job.get("location") == "Unknown":
                        _loc = await self.extract_location_from_page(page)
                        if _loc:
                            job["location"] = _loc
                    
                except Exception as e:
                    logger.warning(f"[{self.site_key}] Failed to fetch description for {job['title']}: {e}")
                finally:
                    await context.close()
                await asyncio.sleep(0.5)
                
            await browser.close()
            
        return jobs

    async def run(self):
        self.print_header()
        jobs_raw = await self.fetch_jobs()
        jobs = [get_job_dict(**job) for job in jobs_raw]
        if not jobs:
            return []
            
        if self.use_filter and self.filter_manager:
            jobs, _, _ = self.apply_title_filter(jobs)
            if not jobs:
                return []
                
        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []
            
        jobs = await self.fetch_job_descriptions(jobs)
        await self.save_results(jobs)
        return jobs
