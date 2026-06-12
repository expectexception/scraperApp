import asyncio
import logging
from typing import List, Dict
from .base_scraper import BaseScraper
from .job_schema import get_job_dict
from playwright.async_api import async_playwright
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class DayforceScraper(BaseScraper):
    """Scraper for Dayforce HCM (e.g. Perimeter Aviation)."""

    def __init__(self, config: Dict, db_manager=None, site_key=None):
        key = site_key if site_key else "dayforce"
        super().__init__(config, site_key=key, db_manager=db_manager)
        
        self.site_config = self.config.get("sites", {}).get(self.site_key, {})
        self.base_url = self.site_config.get("base_url", "https://jobs.dayforcehcm.com")
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
                await page.wait_for_timeout(5000)
                
                # Check for "Load More" button to get more jobs
                for _ in range(5):
                    try:
                        more_btn = page.locator("button:has-text('Load More'), .load-more").first
                        if await more_btn.is_visible():
                            await more_btn.click()
                            await page.wait_for_timeout(3000)
                        else:
                            break
                    except:
                        break

                links = await page.evaluate("""() => {
                    let cards = document.querySelectorAll('[test-id="job-posting-card"]');
                    if (cards.length === 0) {
                        cards = document.querySelectorAll('.ant-list-item, .job-tile, .job-row');
                    }
                    return Array.from(cards).map(card => {
                        let titleEl = card.querySelector('[test-id="job-title"]') || card.querySelector('.job-title') || card.querySelector('h2, h3, a');
                        let aEl = card.querySelector('a[href*="/jobs/"]') || card.querySelector('a');
                        let locEl = card.querySelector('[test-id="job-location"]') || card.querySelector('.job-location, .location');
                        let dateEl = card.querySelector('[test-id="job-posted-date-expiry"]') || card.querySelector('.posted-date');
                        
                        return {
                            t: titleEl ? titleEl.innerText.trim() : "",
                            h: aEl ? aEl.href : "",
                            l: locEl ? locEl.innerText.trim() : "Unknown",
                            d: dateEl ? dateEl.innerText.trim() : ""
                        };
                    }).filter(item => item.h && item.t);
                }""")

                logger.info(f"[{self.site_key}] Found {len(links)} jobs in DOM")

                seen_urls = set()
                job_data_list = []
                for link in links:
                    title = link["t"]
                    job_url = link["h"]
                    location = link["l"]
                    date_raw = link["d"]
                    
                    if not title or not job_url or job_url in seen_urls:
                        continue
                    
                    seen_urls.add(job_url)
                        
                    if not self.should_process_job(title):
                        continue

                    if await self.is_url_already_scraped(job_url):
                        continue
                        
                    clean_date = date_raw
                    if clean_date.lower().startswith("posted"):
                        clean_date = clean_date[6:].strip()
                        if clean_date.startswith(","):
                            clean_date = clean_date[1:].strip()
                    
                    parsed_date = self.parse_posted_date(clean_date)
                        
                    job_data_list.append({
                        "title": title,
                        "url": job_url,
                        "location": location,
                        "posted_date": parsed_date,
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
                            let el = document.querySelector('.job-description') || document.querySelector('.description') || document.querySelector('[data-testid="job-description"]');
                            return el ? el.innerHTML : document.body.innerText;
                        }''')
                    except Exception as e:
                        logger.error(f"[{self.site_key}] Failed to load details for {item['url']}: {e}")

                    job = get_job_dict(
                        job_id=f"{self.site_key}_{hash(item['url'])}",
                        title=item["title"],
                        company=self.company_name,
                        location=item["location"],
                        posted_date=item.get("posted_date"),
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
