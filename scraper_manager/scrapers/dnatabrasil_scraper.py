"""
dnata Brasil Careers Scraper
Extracts aviation job listings from dnatabrasil.gupy.io (Gupy Platform)
"""

import asyncio
import re
from datetime import datetime
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict
from curl_cffi import requests as curl_requests


class DnataBrasilScraper(BaseScraper):
    """Scraper for dnata Brasil Careers (Gupy)"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, "dnatabrasil", db_manager=db_manager)
        self.site_config = config.get("sites", {}).get("dnatabrasil", {})
        self.base_url = self.site_config.get("base_url", "https://dnatabrasil.gupy.io")
        self.subdomain = "dnatabrasil"
        # Gupy API URL
        self.api_url = f"https://portal.api.gupy.io/api/v1/jobs?subdomain={self.subdomain}&limit=100"

    async def run(self):
        """Main execution method"""
        self.print_header()

        self.logger.info(f"Fetching jobs from {self.company_name}...")
        self.logger.info(f"Platform: Gupy (Subdomain: {self.subdomain})")

        # Try API first as it's more reliable and faster
        jobs_raw = await self.fetch_jobs_from_api()

        if not jobs_raw:
            self.logger.info(
                "API result empty or failed, falling back to DOM scraping..."
            )
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

    async def fetch_jobs_from_api(self):
        """Fetch jobs using Gupy's public API using curl_cffi for stability"""
        jobs = []
        try:
            self.logger.info(f"Calling Gupy API: {self.api_url}")

            # Using curl_requests (curl_cffi) to impersonate a browser
            # This is often more stable than Playwright for simple JSON APIs
            response = curl_requests.get(
                self.api_url, impersonate="chrome110", timeout=30
            )

            if response.status_code != 200:
                self.logger.warning(f"API returned status {response.status_code}")
                return []

            data = response.json()
            raw_jobs = data.get("data", [])
            self.logger.info(f"Received {len(raw_jobs)} jobs from API")

            for item in raw_jobs:
                job_id = item.get("id")
                title = item.get("name")
                job_url = item.get("jobUrl") or f"{self.base_url}/jobs/{job_id}"

                # Extract location
                city = item.get("city", "")
                state = item.get("state", "")
                location = (
                    f"{city}, {state}" if city and state else city or state or "Brazil"
                )

                job_data = {
                    "job_id": f"dnata_br_{job_id}",
                    "title": title,
                    "company": self.company_name,
                    "source": self.site_key,
                    "url": job_url,
                    "apply_url": job_url,
                    "location": self.normalize_location(location),
                    "timestamp": datetime.now().isoformat(),
                    "description": "",  # Will be fetched later
                }
                jobs.append(job_data)

                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break

        except Exception as e:
            self.logger.error(f"API Error: {e}")

        return jobs

    async def fetch_jobs_from_listing(self):
        """Fallback DOM scraping for Gupy listing"""
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                self.logger.info(f"Navigating to {self.base_url}")
                await page.goto(self.base_url, wait_until="load", timeout=60000)
                await self.random_delay(3, 5)

                await self.simulate_human_behavior(page)

                # Select all job links
                job_elements = await page.query_selector_all('a[href*="/jobs/"]')
                self.logger.info(f"Found {len(job_elements)} job elements via DOM")

                for el in job_elements:
                    try:
                        href = await el.get_attribute("href")
                        if not href:
                            continue

                        job_url = (
                            f"{self.base_url}{href}" if href.startswith("/") else href
                        )

                        # Extract title and location from child divs
                        divs = await el.query_selector_all("div")
                        if len(divs) >= 2:
                            title = (await divs[0].inner_text()).strip()
                            location = (await divs[1].inner_text()).strip()
                        else:
                            title = (await el.inner_text()).strip()
                            location = "Brazil"

                        # Extract ID from URL
                        match = re.search(r"/jobs/(\d+)", href)
                        if match:
                            job_id = match.group(1)
                        else:
                            import hashlib

                            job_id = hashlib.md5(job_url.encode()).hexdigest()[:8]

                        job_data = {
                            "job_id": f"dnata_br_{job_id}",
                            "title": title,
                            "company": self.company_name,
                            "source": self.site_key,
                            "url": job_url,
                            "apply_url": job_url,
                            "location": self.normalize_location(location),
                            "timestamp": datetime.now().isoformat(),
                            "description": "",
                        }
                        jobs.append(job_data)

                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break
                    except Exception:
                        continue

            except Exception as e:
                self.logger.error(f"DOM Error: {e}")
            finally:
                await context.close()
                await browser.close()

        return jobs

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
        """Extract detailed description from Gupy job page"""
        try:
            page, context = await self.setup_stealth_page(browser)

            # Load job detail page
            await page.goto(job["url"], wait_until="load", timeout=45000)
            await self.random_delay(2, 4)

            # Gupy usually has a section with data-testid="job-description-section"
            desc_selectors = [
                '[data-testid="section-job-description"]',
                'section[class*="JobDescription"]',
                ".job-description",
                "#job-description",
                "main",
                ".content",
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

            await page.close()
            await context.close()

        except Exception:
            pass
