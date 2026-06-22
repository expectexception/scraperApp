import logging
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
import re

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class AirSerbiaScraper(BaseScraper):
    """Scraper for Air Serbia Careers (SuccessFactors)"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, "airserbia", db_manager=db_manager)
        self.site_config = config.get("sites", {}).get("airserbia", {})
        self.base_url = self.site_config.get("base_url", "https://career.airserbia.com")
        # General search endpoint
        self.jobs_url = "https://career.airserbia.com/go/View-all-jobs/9196455/"
        self.company_name = "Air Serbia"

    async def fetch_jobs(self) -> list:
        logger.info(f"[{self.site_key}] Fetching jobs from listing...")
        jobs_raw = await self._fetch_jobs_listing()
        jobs = [get_job_dict(**job) for job in jobs_raw]

        if not jobs:
            return []

        jobs_with_descriptions = await self.fetch_job_descriptions(jobs)
        return jobs_with_descriptions

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()

        if self.use_filter and self.filter_manager:
            matched_jobs, rejected_jobs, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)
            jobs = matched_jobs

        jobs, duplicate_count = await self.filter_new_jobs(jobs)
        await self.save_results(jobs)
        self.print_sample(jobs)
        return jobs

    async def _fetch_jobs_listing(self):
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                ignore_https_errors=True,
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            page = await context.new_page()

            try:
                print(f"Loading {self.company_name} careers page...")
                await self.random_delay(1, 2)
                await page.goto(
                    self.jobs_url, wait_until="domcontentloaded", timeout=45000
                )

                await self.random_delay(4, 6)
                await self.simulate_human_behavior(page)

                job_links = await page.evaluate("""() => {
                    let links = Array.from(document.querySelectorAll('a.jobTitle-link'));
                    return links.map(a => {
                        let row = a.closest('tr');
                        let loc = row ? row.querySelector('span.jobLocation') : null;
                        return {
                            href: a.href,
                            title: a.innerText.trim(),
                            location: loc ? loc.innerText.trim() : 'Belgrade/Serbia'
                        };
                    });
                }""")

                unique_links = {}
                for l in job_links:
                    if l["href"] not in unique_links:
                        unique_links[l["href"]] = l

                print(f"✓ Found {len(unique_links)} jobs")

                if not unique_links:
                    return jobs

                for href, l in (
                    list(unique_links.items())[: self.max_jobs]
                    if self.max_jobs
                    else unique_links.items()
                ):
                    try:
                        job_url = (
                            href
                            if href.startswith("http")
                            else f"{self.base_url}{href}"
                        )
                        title = l.get("title", "")
                        location = l.get("location", "Belgrade/Serbia")

                        # Pre-scrape title filtering
                        if not self.should_process_job(title):
                            continue

                        job_id = None
                        match = re.search(r"/(\d+)/?$", job_url)
                        if match:
                            job_id = match.group(1)
                        if not job_id:
                            job_id = f"airserbia_{len(jobs) + 1}"

                        job_data = {
                            "job_id": f"airserbia_{job_id}",
                            "title": title,
                            "company": self.company_name,
                            "source": self.site_key,
                            "url": job_url,
                            "apply_url": job_url,
                            "location": location,
                            "timestamp": datetime.now().isoformat(),
                        }
                        jobs.append(job_data)
                    except Exception:
                        continue

            except Exception as e:
                print(f"❌ Error fetching jobs: {e}")
            finally:
                await context.close()
                await browser.close()
        return jobs

    async def fetch_job_descriptions(self, jobs):
        print(f"\nFetching detailed descriptions for {len(jobs)} jobs...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)

            for i in range(0, len(jobs), self.batch_size):
                batch = jobs[i : i + self.batch_size]
                tasks = []

                for job in batch:
                    if job.get("url"):
                        tasks.append(self._extract_description(browser, job))

                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

                print(
                    f"  Processed {min(i + self.batch_size, len(jobs))}/{len(jobs)} jobs"
                )

            await browser.close()

        with_desc = sum(1 for job in jobs if job.get("description"))
        print(f"✓ Successfully extracted {with_desc}/{len(jobs)} descriptions")

        return jobs

    async def _extract_description(self, browser, job):
        try:
            context = await browser.new_context(
                ignore_https_errors=True,
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            page = await context.new_page()
            await self.random_delay(1, 2)
            await page.goto(job["url"], wait_until="domcontentloaded", timeout=45000)
            await self.random_delay(2, 4)
            await self.simulate_human_behavior(page)

            location_selectors = [
                "#job-location",
                'span[data-careersite-propertyid="location"]',
                "span.job-location",
                ".job-location",
            ]
            for selector in location_selectors:
                try:
                    loc_elem = await page.query_selector(selector)
                    if loc_elem:
                        loc_text = await loc_elem.inner_text()
                        if loc_text and len(loc_text) > 2:
                            job["location"] = loc_text.strip()
                            break
                except Exception:
                    continue

            desc_selectors = [
                ".jobdescription",
                "#jobDescription",
                '[itemprop="description"]',
            ]
            description = ""
            for selector in desc_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        text = await elem.inner_text()
                        if text and len(text) > 100:
                            description = text.strip()
                            break
                except Exception:
                    continue

            if not description:
                description = await self.extract_description_from_page(page)

            posted_date = await self.extract_posted_date_from_page(page)
            if posted_date:
                job["posted_date"] = posted_date

            job["description"] = description
            # Backfill location from the original posting when missing.
            if not job.get("location") or job.get("location") == "Unknown":
                _loc = await self.extract_location_from_page(page)
                if _loc:
                    job["location"] = _loc

            await page.close()
            await context.close()

        except Exception as e:
            print(f"  Error fetching description for {job['job_id']}: {e}")
