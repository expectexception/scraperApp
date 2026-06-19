import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright
import re

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class AviationCareersScraper(BaseScraper):
    """
    Scraper for Aviation Careers (Taleo)
    URL: https://aviationcareers.ca/careersection/2/jobsearch.ftl?lang=en#
    """
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="aviationcareers", db_manager=db_manager)
        self.base_url = "https://aviationcareers.ca/careersection/2/jobsearch.ftl?lang=en"
        self.company_name = "Aviation Careers CA"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                # Keywords to search
                keywords = ["aviation", "flight", "operations", "dispatch", "maintenance", "crew", "pilot", "ground", "airport"]
                seen_job_urls = set()

                for keyword in keywords:
                    if self.max_jobs and len(jobs) >= self.max_jobs: break
                    
                    try:
                        logger.info(f"[{self.site_key}] Navigating to {self.base_url} and searching for '{keyword}'...")
                        await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
                        await page.wait_for_timeout(3000)

                        # Find keyword input
                        keyword_input = None
                        for selector in ['input[id*="KEYWORD" i]', 'input[name*="keyword" i]', '#keyword', '.keyword-input']:
                            try:
                                el = await page.query_selector(selector)
                                if el and await el.is_visible():
                                    keyword_input = el
                                    break
                            except:
                                pass

                        if keyword_input:
                            await keyword_input.fill("")
                            await keyword_input.type(keyword, delay=100)
                            
                            # Click search button
                            search_btn = None
                            for selector in ['#search', '#searchButton', 'input[type="submit"]', 'a:has-text("Search")']:
                                try:
                                    el = await page.query_selector(selector)
                                    if el and await el.is_visible():
                                        search_btn = el
                                        break
                                except:
                                    pass
                                    
                            if search_btn:
                                await search_btn.click()
                                await page.wait_for_timeout(5000)
                            else:
                                await keyword_input.press("Enter")
                                await page.wait_for_timeout(5000)

                        # Wait for job list
                        try:
                            await page.wait_for_selector('a[href*="jobdetail.ftl"]', timeout=10000)
                        except:
                            logger.info(f"[{self.site_key}] No jobs loaded for keyword '{keyword}'.")
                            continue

                        # Extract job links
                        links = await page.evaluate("""() => {
                            return Array.from(document.querySelectorAll('a[href*="jobdetail.ftl"]'))
                                .map(a => ({t: a.innerText.trim(), h: a.href}))
                                .filter(a => a.t && a.t.length > 3)
                        }""")

                        logger.info(f"[{self.site_key}] Found {len(links)} job links for '{keyword}'")

                        for link in links:
                            if self.max_jobs and len(jobs) >= self.max_jobs: break

                            url = link["h"]
                            title = link["t"]

                            if url in seen_job_urls:
                                continue
                            seen_job_urls.add(url)

                            if not self.is_job_link(title, url):
                                continue

                            try:
                                if not self.should_process_job(title):
                                    continue

                                if await self.is_url_already_scraped(url):
                                    continue

                                logger.info(f"[{self.site_key}] Fetching details for: {url}")
                                detail_page = await context.new_page()
                                await detail_page.goto(url, wait_until="domcontentloaded", timeout=30000)
                                await detail_page.wait_for_timeout(2000)

                                real_title = title
                                h1 = detail_page.locator("h1").first
                                if await h1.is_visible():
                                    extracted = await h1.inner_text()
                                    if len(extracted) > 5:
                                        real_title = extracted

                                description = await self.extract_description_from_page(detail_page)
                                location = "Canada"
                                
                                loc_text = await detail_page.evaluate("""() => {
                                    let fields = Array.from(document.querySelectorAll('.editableschematicfield label'));
                                    for(let f of fields) {
                                        if(f.innerText.includes('Location')) {
                                            return f.nextElementSibling ? f.nextElementSibling.innerText.trim() : "";
                                        }
                                    }
                                    return "";
                                }""")
                                if loc_text:
                                    location = loc_text

                                posted_date = await self.extract_posted_date_from_page(detail_page)

                                job_id = f"aviationcareers_{hash(url)}"
                                match = re.search(r"job=([^&]+)", url)
                                if match:
                                    job_id = f"aviationcareers_{match.group(1)}"

                                job = get_job_dict(
                                    job_id=job_id,
                                    title=real_title,
                                    company=self.company_name,
                                    location=location,
                                    url=url,
                                    source_url=self.base_url,
                                    description=description,
                                    apply_url=url,
                                    posted_date=posted_date,
                                    source=self.site_key,
                                )

                                jobs.append(job)
                                await detail_page.close()

                            except Exception as e:
                                logger.error(f"[{self.site_key}] Error parsing job detail ({url}): {e}")
                                continue
                                
                    except Exception as e:
                        logger.error(f"[{self.site_key}] Error processing keyword '{keyword}': {e}")
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

        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
