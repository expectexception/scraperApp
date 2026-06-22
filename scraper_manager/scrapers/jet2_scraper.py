import asyncio
import logging
import re
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class Jet2Scraper(BaseScraper):
    """
    Scraper for Jet2
    URL: https://jet2careers.com/search-careers/ -> Brassring
    """

    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="jet2", db_manager=db_manager)
        self.base_url = "https://jet2careers.com/search-careers/"
        self.brassring_url = "https://krb-sjobs.brassring.com/TGNewUI/Search/Home/Home?partnerid=30013&siteid=5476#home"
        self.company_name = "Jet2"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            try:
                page, context = await self.setup_stealth_page(browser)
                
                logger.info(f"[{self.site_key}] Navigating to {self.brassring_url}...")
                await page.goto(self.brassring_url, wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(3000)

                # Hide cookie banner to avoid pointer event interception
                await page.evaluate('''() => {
                    const banner = document.querySelector('#onetrust-consent-sdk');
                    if (banner) banner.style.display = 'none';
                }''')
                await page.wait_for_timeout(1000)

                # Click search button
                logger.info(f"[{self.site_key}] Searching jobs on Brassring...")
                search_btn = await page.query_selector("button:has-text('Search'), button.submitBtn")
                if search_btn:
                    await search_btn.click()
                else:
                    logger.warning(f"[{self.site_key}] Could not find Search button")
                
                await page.wait_for_timeout(8000)
                
                # Check for "Show More Jobs" and click it multiple times to load more
                for i in range(5):
                    has_more = await page.evaluate('''() => {
                        const showMoreBtn = document.querySelector('.show-more-button, button[title*="Show more"]');
                        if (showMoreBtn) {
                            showMoreBtn.click();
                            return true;
                        }
                        return false;
                    }''')
                    if has_more:
                        await page.wait_for_timeout(3000)
                    else:
                        break

                # Extract jobs
                extracted_jobs = await page.evaluate('''() => {
                    const links = Array.from(document.querySelectorAll('a'));
                    return links.map(a => ({
                        title: a.innerText.trim(),
                        href: a.href || "",
                    })).filter(j => j.href.toLowerCase().includes('jobdetails') && j.title.length > 5);
                }''')

                logger.warning(f"[{self.site_key}] Found {len(extracted_jobs)} jobs on Brassring total (pre-filter)")
                for j in extracted_jobs[:5]:
                    logger.warning(j['title'])

                for job_data in extracted_jobs:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    title = job_data["title"].split("\\n")[0].strip()
                    url = job_data["href"]
                    
                    if not self.should_process_job(title):
                        continue

                    job_id_match = re.search(r"jobId=([0-9]+)", url)
                    job_id = job_id_match.group(1) if job_id_match else f"jet2_{hash(url)}"

                    job = get_job_dict(
                        job_id=job_id,
                        title=title,
                        company=self.company_name,
                        location="UK", # default from pinpoint
                        url=url,
                        source_url=self.brassring_url,
                        description="",
                        apply_url=url,
                        source=self.site_key,
                    )
                    jobs.append(job)

                # Also fetch from WordPress direct vacancies page: https://jet2careers.com/vacancy/
                logger.info(f"[{self.site_key}] Fetching WordPress direct vacancies from https://jet2careers.com/vacancy/...")
                try:
                    await page.goto("https://jet2careers.com/vacancy/", wait_until="networkidle", timeout=60000)
                    wp_jobs = await page.evaluate('''() => {
                        let items = Array.from(document.querySelectorAll(".job-item"));
                        return items.map(el => {
                            let a = el.querySelector("a.job-url");
                            let titleEl = el.querySelector(".job-title");
                            let locEl = el.querySelector(".job-location");
                            let postedEl = el.querySelector(".job-posted-date");
                            return {
                                href: a ? a.href : "",
                                title: titleEl ? titleEl.innerText.trim() : "",
                                location: locEl ? locEl.innerText.trim() : "",
                                posted_date: postedEl ? postedEl.innerText.trim() : ""
                            };
                        }).filter(j => j.href && j.title);
                    }''')
                    
                    logger.info(f"[{self.site_key}] Found {len(wp_jobs)} jobs on WordPress vacancies page")
                    for wj in wp_jobs:
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break
                            
                        title = wj["title"]
                        url = wj["href"]
                        location = wj["location"]
                        posted_date = wj["posted_date"]
                        
                        if not self.should_process_job(title):
                            continue
                            
                        job_id_match = re.search(r"vacancy/([0-9]+)", url)
                        job_id = f"jet2_wp_{job_id_match.group(1)}" if job_id_match else f"jet2_{hash(url)}"
                        
                        # Check duplicate
                        if any(x["job_id"] == job_id or x["url"] == url for x in jobs):
                            continue
                            
                        job = get_job_dict(
                            job_id=job_id,
                            title=title,
                            company=self.company_name,
                            location=location or "UK",
                            url=url,
                            source_url="https://jet2careers.com/vacancy/",
                            description="",
                            apply_url=url,
                            source=self.site_key,
                        )
                        if posted_date:
                            job["posted_date"] = posted_date
                        jobs.append(job)
                except Exception as e:
                    logger.warning(f"[{self.site_key}] Failed to scrape WordPress vacancies: {e}")

            except Exception as e:
                logger.error(f"[{self.site_key}] Global error in fetch_jobs: {e}")
            finally:
                if 'context' in locals():
                    await context.close()
                await browser.close()
                
        return jobs

    async def fetch_job_descriptions(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not jobs:
            return []
            
        logger.info(f"[{self.site_key}] Fetching descriptions for {len(jobs)} jobs...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            try:
                for job in jobs:
                    page, context = await self.setup_stealth_page(browser)
                    try:
                        await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_timeout(3000)

                        desc = await page.evaluate('''() => {
                            const descEl = document.querySelector('.vacancy-description, .vacancy-main-content, .job-description, .jobDescription, .QuestionBody');
                            return descEl ? descEl.innerText : document.body.innerText;
                        }''')
                        
                        job["description"] = desc.strip()[:3000]

                    except Exception as e:
                        logger.warning(f"[{self.site_key}] Failed to fetch description for {job['title']}: {e}")
                    finally:
                        await context.close()
            finally:
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
