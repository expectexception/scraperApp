import asyncio
import logging
import re
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class HKExpressScraper(BaseScraper):
    """
    Scraper for HK Express
    URL: https://careers.hkexpress.com/en/listing/
    """
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="hkexpress", db_manager=db_manager)
        self.base_url = "https://careers.hkexpress.com/en/listing/?page-items=100"
        self.company_name = "HK Express"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(5000)

                # Extract links
                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll("a"))
                        .map(a => ({ href: a.href, text: a.innerText || a.textContent }))
                        .filter(l => l.href && l.href.includes("/job/"));
                }''')

                # Dedup
                seen_urls = set()
                unique_links = []
                for link in links:
                    url = link["href"]
                    if url not in seen_urls:
                        seen_urls.add(url)
                        unique_links.append(link)

                logger.info(f"[{self.site_key}] Found {len(unique_links)} potential job links.")

                for link in unique_links:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    title = link["text"].strip().replace("\n", " ")
                    url = link["href"]

                    if not self.is_job_link(title, url):
                        continue
                    if not self.should_process_job(title):
                        continue
                    if await self.is_url_already_scraped(url):
                        continue

                    job_id_match = re.search(r"/job/(\d+)", url)
                    job_id = f"hkexpress_{job_id_match.group(1)}" if job_id_match else f"hkexpress_{abs(hash(url)) % 10000000}"

                    jobs.append({
                        "job_id": job_id,
                        "title": title,
                        "company": self.company_name,
                        "source": self.site_key,
                        "url": url,
                        "apply_url": url,
                    })

            except Exception as e:
                logger.error(f"[{self.site_key}] Global error in fetch_jobs: {e}")
            finally:
                await context.close()
                await browser.close()
        return jobs

    async def fetch_job_descriptions(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not jobs:
            return []
        logger.info(f"[{self.site_key}] Fetching details/descriptions for {len(jobs)} jobs...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            for job in jobs:
                try:
                    page, context = await self.setup_stealth_page(browser)
                    await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(2000)

                    # Extract location
                    location = "Hong Kong"
                    loc_el = await page.query_selector("span.location, p:has-text('Location:') span, li:has-text('Location:') span")
                    if not loc_el:
                        # Fallback: search text in page
                        loc_text = await page.evaluate('''() => {
                            const labels = Array.from(document.querySelectorAll("span, p, li, strong"));
                            for (const el of labels) {
                                if (el.innerText && el.innerText.includes("Location:")) {
                                    return el.innerText.replace("Location:", "").trim();
                                }
                            }
                            return "";
                        }''')
                        if loc_text:
                            location = loc_text
                    else:
                        location = await loc_el.inner_text()

                    # Extract description
                    desc = ""
                    desc_el = await page.query_selector(".job-details, #job-details, .job-details-container")
                    if desc_el:
                        desc = await desc_el.inner_text()
                    else:
                        desc = await self.extract_description_from_page(page)

                    job["location"] = location.strip()
                    job["description"] = desc.strip()

                    # Try to extract advertised date as posted_date
                    adv_text = await page.evaluate('''() => {
                        const labels = Array.from(document.querySelectorAll("span, p, li, strong"));
                        for (const el of labels) {
                            if (el.innerText && el.innerText.includes("Advertised:")) {
                                return el.innerText.replace("Advertised:", "").trim();
                            }
                        }
                        return "";
                    }''')
                    if adv_text:
                        job["posted_date"] = self.parse_posted_date(adv_text)

                except Exception as e:
                    logger.warning(f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}")
                    job["location"] = "Hong Kong"
                    job["description"] = ""
                finally:
                    await context.close()
                await self.random_delay(1, 2)
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
