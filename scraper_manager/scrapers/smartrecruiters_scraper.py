import asyncio
import logging
from typing import List, Dict
from .base_scraper import BaseScraper
from .job_schema import get_job_dict
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class SmartRecruitersScraper(BaseScraper):
    """Scraper for SmartRecruiters (e.g. Etihad Airways)."""

    def __init__(self, config: Dict, db_manager=None, site_key=None):
        key = site_key if site_key else "smartrecruiters"
        super().__init__(config, site_key=key, db_manager=db_manager)
        
        self.site_config = self.config.get("sites", {}).get(self.site_key, {})
        self.jobs_url = self.site_config.get("jobs_url", "")
        self.company_name = self.site_config.get("name", "Unknown Company")

    async def fetch_jobs(self) -> List[Dict]:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                logger.info(f"[{self.site_key}] Navigating to {self.jobs_url}...")
                await page.goto(self.jobs_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)
                
                # Check for "Show more jobs" button
                for _ in range(10):
                    try:
                        more_btn = page.locator("button:has-text('more'), a:has-text('more jobs'), .sr-button").first
                        if await more_btn.is_visible():
                            await more_btn.click()
                            await page.wait_for_timeout(2000)
                        else:
                            break
                    except:
                        break

                links = await page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('a[href*="jobs.smartrecruiters.com"]')).map(a => {
                        let title = a.querySelector('h3, h4, .title, .job-title');
                        let text = title ? title.innerText.trim() : a.innerText.trim().split('\\n')[0];
                        
                        let locEl = a.querySelector('.location, .details, span');
                        let loc = locEl ? locEl.innerText.trim() : "Unknown";
                        
                        return { t: text, h: a.href, l: loc };
                    });
                }""")

                logger.info(f"[{self.site_key}] Found {len(links)} jobs in DOM")

                seen_urls = set()
                job_data_list = []
                for link in links:
                    title = link["t"]
                    job_url = link["h"]
                    location = link["l"]
                    
                    if not title or not job_url or job_url in seen_urls:
                        continue
                        
                    seen_urls.add(job_url)
                        
                    if not self.should_process_job(title):
                        continue

                    if await self.is_url_already_scraped(job_url):
                        continue
                        
                    job_data_list.append({
                        "title": title,
                        "url": job_url,
                        "location": location,
                    })
                    
                    if self.max_jobs and len(job_data_list) >= self.max_jobs:
                        break

                for item in job_data_list:
                    logger.info(f"[{self.site_key}] Fetching details for: {item['title']}...")
                    
                    desc_text = "Description not found."
                    
                    try:
                        await page.goto(item["url"], wait_until="domcontentloaded", timeout=60000)
                        await page.wait_for_timeout(2000)
                        
                        desc_text = await page.evaluate('''() => {
                            let el = document.querySelector('.job-sections') || document.querySelector('[itemprop="description"]');
                            return el ? el.innerHTML : document.body.innerText;
                        }''')
                    except Exception as e:
                        logger.error(f"[{self.site_key}] Failed to load details for {item['url']}: {e}")

                    job = get_job_dict(
                        job_id=f"{self.site_key}_{hash(item["url"])}",
                        title=item["title"],
                        company=self.company_name,
                        location=item["location"],
                        url=item["url"],
                        source_url=self.base_url if hasattr(self, 'base_url') else item["url"],
                        description=desc_text,
                        apply_url=item["url"],
                        source=self.site_key
                    )
                    jobs.append(job)

                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                return jobs

            except Exception as e:
                logger.error(f"[{self.site_key}] Scraper failed: {e}")
                return jobs
            finally:
                await browser.close()

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        matched_jobs, rejected_jobs, stats = self.apply_title_filter(jobs)
        await self.save_results(matched_jobs)
        return matched_jobs
