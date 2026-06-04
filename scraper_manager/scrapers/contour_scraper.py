import asyncio
import logging
from typing import List, Dict
from .base_scraper import BaseScraper
from .job_schema import get_job_dict
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class ContourScraper(BaseScraper):
    """Scraper for Contour Aviation (Paycom) via Playwright API Interception."""

    def __init__(self, config: Dict, db_manager=None):
        super().__init__(config, site_key="contour", db_manager=db_manager)
        self.base_url = self.config.get(
            "jobs_url", 
            "https://www.paycomonline.net/v4/ats/web.php/portal/4E8FCB0F31AC88147F0DB7B85238B354/career-page"
        )
        self.company_name = self.config.get("name", "Contour Aviation")

    async def fetch_jobs(self) -> List[Dict]:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            api_jobs_data = []

            async def handle_response(response):
                if 'job-posting-previews/search' in response.url:
                    try:
                        text = await response.text()
                        import json
                        data = json.loads(text)
                        for job in data.get("jobPostingPreviews", []):
                            api_jobs_data.append(job)
                    except Exception as e:
                        logger.warning(f"[{self.site_key}] Failed to parse jobs JSON: {e}")

            page.on('response', handle_response)

            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(5000)
                
                logger.info(f"[{self.site_key}] Intercepted {len(api_jobs_data)} jobs from API")
                
                job_data_list = []
                for item in api_jobs_data:
                    title = item.get("jobTitle", "").strip()
                    job_id = item.get("jobId")
                    location = item.get("locations", "Unknown").strip()
                    
                    if not title or not job_id:
                        continue
                        
                    base_parts = self.base_url.split('/career-page')
                    if len(base_parts) > 1:
                        job_url = f"{base_parts[0]}/jobs/{job_id}"
                    else:
                        job_url = f"https://www.paycomonline.net/v4/ats/web.php/portal/4E8FCB0F31AC88147F0DB7B85238B354/jobs/{job_id}"
                    
                    if not self.should_process_job(title):
                        continue

                    if await self.is_url_already_scraped(job_url):
                        continue
                        
                    job_data_list.append({
                        "title": title,
                        "url": job_url,
                        "location": location,
                        "api_id": job_id
                    })
                    
                    if self.max_jobs and len(job_data_list) >= self.max_jobs:
                        break

                for item in job_data_list:
                    logger.info(f"[{self.site_key}] Fetching details for: {item['title']}...")
                    
                    desc_text = "Description not found."
                    details_intercepted = {}
                    
                    async def handle_detail_resp(response):
                        if f"job-postings/{item['api_id']}" in response.url:
                            try:
                                txt = await response.text()
                                import json
                                data = json.loads(txt)
                                d = data.get("jobPosting", {}).get("description", "")
                                if d:
                                    details_intercepted["desc"] = d
                            except:
                                pass

                    page.on('response', handle_detail_resp)
                    
                    try:
                        await page.goto(item["url"], wait_until="networkidle", timeout=60000)
                        await page.wait_for_timeout(2000)
                        
                        if "desc" in details_intercepted:
                            desc_text = details_intercepted["desc"]
                        else:
                            try:
                                desc_text = await page.evaluate('''() => {
                                    let el = document.querySelector('.job-description') || document.querySelector('.description') || document.querySelector('[data-testid="job-description"]');
                                    return el ? el.innerHTML : document.body.innerText;
                                }''')
                            except:
                                pass
                                
                    except Exception as e:
                        logger.error(f"[{self.site_key}] Failed to load details for {item['url']}: {e}")
                        
                    page.remove_listener('response', handle_detail_resp)

                    job = get_job_dict(
                        job_id=f"contour_{item['api_id']}",
                        title=item["title"],
                        company=self.company_name,
                        location=item["location"],
                        url=item["url"],
                        source_url=self.base_url,
                        description=desc_text,
                        apply_url=item["url"],
                        posted_date=None,
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
