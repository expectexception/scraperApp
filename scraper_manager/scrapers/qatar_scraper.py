"""
Qatar Airways Careers Scraper
Extracts aviation job listings from careers.qatarairways.com
"""

import asyncio
import re
from datetime import datetime
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict


class QatarAirwaysScraper(BaseScraper):
    """Scraper for Qatar Airways Careers"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, "qatar", db_manager=db_manager)
        self.site_config = config.get("sites", {}).get("qatar", {})
        self.base_url = self.site_config.get(
            "base_url", "https://careers.qatarairways.com"
        )
        # Default jobs URL if not provided in config
        self.jobs_url = self.site_config.get(
            "jobs_url", "https://careers.qatarairways.com/global/SearchJobs/"
        )
        self.records_per_page = 6  # Fixed by server currently

    async def run(self):
        """Main execution method"""
        self.print_header()

        print(f"Fetching jobs from {self.site_config.get('name', 'Qatar Airways')}...")
        print(f"URL: {self.jobs_url}\n")

        jobs_raw = await self.fetch_jobs_from_listing()
        jobs = [get_job_dict(**job) for job in jobs_raw]

        if not jobs:
            print("❌ No jobs found")
            return []

        print(f"\n✓ Extracted {len(jobs)} jobs from listing")

        # Apply title filtering BEFORE fetching descriptions
        if self.use_filter and self.filter_manager:
            print("\n🔍 Applying title filter...")
            matched_jobs, rejected_jobs, filter_stats = self.apply_title_filter(jobs)

            if not matched_jobs:
                print("❌ No jobs matched the filter criteria")
                return []

            print(
                f"✓ {len(matched_jobs)} jobs matched filter (will fetch descriptions)"
            )
            print(f"✗ {len(rejected_jobs)} jobs rejected (not relevant)")
            jobs = matched_jobs

        # Filter duplicates
        jobs, duplicate_count = await self.filter_new_jobs(jobs)
        if duplicate_count > 0:
            print(f"\n🔄 Filtered out {duplicate_count} duplicate jobs")

        if not jobs:
            print("✓ All jobs are already in database or filtered out")
            return []

        # Fetch detailed descriptions
        jobs_with_descriptions = await self.fetch_job_descriptions(jobs)

        # Save results
        await self.save_results(jobs_with_descriptions)
        self.print_sample(jobs_with_descriptions)

        return jobs_with_descriptions

    async def fetch_jobs_from_listing(self):
        """Fetch jobs from Qatar Airways listing page with pagination"""
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                # Pagination using jobOffset
                # We'll crawl until max_jobs or no more result cards
                for offset in range(0, 300, self.records_per_page):
                    separator = "&" if "?" in self.jobs_url else "?"
                    current_url = f"{self.jobs_url}{separator}jobRecordsPerPage={self.records_per_page}&jobOffset={offset}"
                    print(f"Loading Qatar Airways careers page (offset={offset})...")

                    await page.goto(current_url, wait_until="load", timeout=45000)
                    await self.random_delay(3, 5)
                    await self.simulate_human_behavior(page)

                    # Wait for job cards/links
                    # Based on exploration, jobs are in blocks with a.link
                    try:
                        await page.wait_for_selector("a.link", timeout=20000)
                    except Exception:
                        print(f"ℹ️  No more results found at offset={offset}")
                        break

                    # Find all links that look like job links (contain /JobDetail/)
                    links = await page.query_selector_all(
                        'a.link, a[href*="/JobDetail/"]'
                    )

                    if not links:
                        print(f"ℹ️  No job links found at offset={offset}")
                        break

                    print(f"✓ Found {len(links)} potential job links on this page")

                    for link in links:
                        try:
                            href = await link.get_attribute("href")
                            if not href or "/JobDetail/" not in href:
                                continue

                            title = (await link.inner_text()).strip()
                            if not title:
                                # Try to get title from aria-label or title attribute
                                title = await link.get_attribute(
                                    "aria-label"
                                ) or await link.get_attribute("title")

                            if not title:
                                continue

                            job_url = (
                                f"{self.base_url}{href}"
                                if href.startswith("/")
                                else href
                            )

                            # Extract Req ID from URL
                            req_id = None
                            match = re.search(r"/JobDetail/(\d+)", href)
                            if match:
                                req_id = match.group(1)

                            if not req_id:
                                # Fallback ID from URL hash or something
                                import hashlib

                                req_id = hashlib.md5(job_url.encode()).hexdigest()[:8]

                            job_data = {
                                "job_id": f"qatar_{req_id}",
                                "title": title,
                                "company": "Qatar Airways",
                                "source": self.site_key,
                                "url": job_url,
                                "apply_url": job_url,
                                "location": "Unknown",
                                "timestamp": datetime.now().isoformat(),
                                "description": "",
                            }
                            jobs.append(job_data)

                            if self.max_jobs and len(jobs) >= self.max_jobs:
                                break
                        except Exception:
                            continue

                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    # Check if we got fewer than 6 results (last page)
                    # Use unique URLs to count
                    current_page_count = len(
                        set(j["url"] for j in jobs[-self.records_per_page :])
                    )
                    if current_page_count < self.records_per_page:
                        break

            except Exception as e:
                print(f"❌ Error fetching jobs: {e}")
            finally:
                await context.close()
                await browser.close()

        # Remove duplicates from the same run
        unique_jobs = []
        seen_urls = set()
        for job in jobs:
            if job["url"] not in seen_urls:
                unique_jobs.append(job)
                seen_urls.add(job["url"])

        return unique_jobs

    async def fetch_job_descriptions(self, jobs):
        """Fetch detailed descriptions for each job"""
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

        # Count jobs with descriptions
        with_desc = sum(1 for job in jobs if job.get("description"))
        print(f"✓ Successfully extracted {with_desc}/{len(jobs)} descriptions")

        return jobs

    async def _extract_description(self, browser, job):
        """Extract detailed description and metadata from Qatar Airways job page"""
        try:
            page, context = await self.setup_stealth_page(browser)

            # Load job detail page
            await page.goto(job["url"], wait_until="load", timeout=45000)
            await self.random_delay(2, 4)
            await self.simulate_human_behavior(page)

            # Wait for content to render (React site)
            try:
                await page.wait_for_selector(
                    "div.description, .job-details, .content", timeout=20000
                )
            except Exception:
                pass

            # Extract metadata (Location, closing date, etc.)
            body_text = await page.inner_text("body")

            # Location extraction using labels
            loc_patterns = [
                r"Work locations:?\s*([^\n\r|]+)",
                r"Location:?\s*([^\n\r|]+)",
                r"Work location:?\s*([^\n\r|]+)",
            ]
            for pattern in loc_patterns:
                match = re.search(pattern, body_text, re.IGNORECASE)
                if match:
                    loc = match.group(1).strip()
                    if loc and len(loc) < 100:
                        job["location"] = self.normalize_location(loc)
                        break

            # Closing date extraction
            closing_patterns = [
                r"Closing date:?\s*([^\n\r|]+)",
                r"Apply before:?\s*([^\n\r|]+)",
            ]
            for pattern in closing_patterns:
                match = re.search(pattern, body_text, re.IGNORECASE)
                if match:
                    date_text = match.group(1).strip()
                    parsed = self.parse_posted_date(date_text)
                    if parsed:
                        job["closing_date"] = parsed
                        break

            # Build description from common selectors
            desc_selectors = [
                "div.description",
                ".job-description",
                ".job-details",
                'div[class*="description"]',
                'div[class*="content"]',
            ]

            description = ""
            for selector in desc_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        text = await elem.inner_text()
                        if text and len(text) > 200:
                            description = text.strip()
                            break
                except Exception:
                    continue

            if not description:
                description = await self.extract_description_from_page(page)

            job["description"] = description
            # Backfill location from the original posting when missing.
            if not job.get("location") or job.get("location") == "Unknown":
                _loc = await self.extract_location_from_page(page)
                if _loc:
                    job["location"] = _loc

            # Extract posted date fallback
            if not job.get("posted_date"):
                posted_date = await self.extract_posted_date_from_page(page)
                if posted_date:
                    job["posted_date"] = posted_date

            await page.close()
            await context.close()

        except Exception:
            # Silence errors for individual jobs to avoid breaking the batch
            pass
