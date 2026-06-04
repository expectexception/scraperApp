import asyncio
import logging
import re
from typing import List, Dict
from datetime import datetime
from .base_scraper import BaseScraper
from .job_schema import get_job_dict
from playwright.async_api import async_playwright
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class BombardierScraper(BaseScraper):
    """Scraper for Bombardier (SuccessFactors/Eightfold)."""

    def __init__(self, config: Dict, db_manager=None, site_key=None):
        key = site_key if site_key else "bombardier"
        super().__init__(config, site_key=key, db_manager=db_manager)
        
        self.site_config = self.config.get("sites", {}).get(self.site_key, {})
        self.base_url = self.site_config.get("base_url", "https://jobs.bombardier.com")
        self.jobs_url = self.site_config.get("jobs_url", "https://jobs.bombardier.com/search/?q=&locationsearch=&searchResultView=LIST&pageNumber=1")
        self.company_name = self.site_config.get("name", "Bombardier")

    async def fetch_jobs(self) -> List[Dict]:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            try:
                seen_urls = set()
                job_data_list = []
                
                # Bombardier uses pagination
                for p_num in range(1, self.max_pages + 1):
                    page = await context.new_page()
                    
                    # Update pageNumber in URL
                    current_url = re.sub(r"pageNumber=\d+", f"pageNumber={p_num}", self.jobs_url)
                    if "pageNumber=" not in current_url:
                        sep = "&" if "?" in current_url else "?"
                        current_url = f"{current_url}{sep}pageNumber={p_num}"
                        
                    logger.info(f"[{self.site_key}] Navigating to {current_url}...")
                    
                    try:
                        await page.goto(current_url, wait_until="domcontentloaded", timeout=60000)
                        await page.wait_for_timeout(3000)
                        
                        links = await page.evaluate("""() => {
                            return Array.from(document.querySelectorAll('a.jobTitle-link, .job-title a, a[href*="/job/"]')).map(a => {
                                let locEl = a.closest('tr') ? a.closest('tr').querySelector('.jobLocation') : null;
                                let loc = locEl ? locEl.innerText.trim() : "Unknown";
                                return {
                                    h: a.href,
                                    t: a.innerText.trim(),
                                    l: loc
                                };
                            });
                        }""")
                        
                        logger.info(f"[{self.site_key}] Found {len(links)} jobs on page {p_num}")
                        
                        added_new = False
                        for link in links:
                            title = link["t"]
                            job_url = link["h"]
                            location = link["l"]
                            
                            if not title or not job_url or job_url in seen_urls:
                                continue
                                
                            seen_urls.add(job_url)
                            added_new = True
                            
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
                                
                        await page.close()
                        
                        if not added_new or (self.max_jobs and len(job_data_list) >= self.max_jobs):
                            break
                            
                    except Exception as e:
                        logger.error(f"[{self.site_key}] Error on page {p_num}: {e}")
                        await page.close()
                        break

                for item in job_data_list:
                    logger.info(f"[{self.site_key}] Fetching details for: {item['title']}...")
                    
                    desc_text = "Description not found."
                    page = await context.new_page()
                    
                    try:
                        await page.goto(item["url"], wait_until="domcontentloaded", timeout=60000)
                        await page.wait_for_timeout(2000)
                        
                        desc_text = await page.evaluate('''() => {
                            let el = document.querySelector('.job-description') || document.querySelector('.jobdescription') || document.querySelector('#jobDescription') || document.querySelector('[itemprop="description"]');
                            return el ? el.innerHTML : document.body.innerText;
                        }''')
                    except Exception as e:
                        logger.error(f"[{self.site_key}] Failed to load details for {item['url']}: {e}")
                    finally:
                        await page.close()

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
