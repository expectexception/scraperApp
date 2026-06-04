"""
Signature Aviation Scraper
Extracts jobs from Signature Aviation Oracle Cloud HCM API
"""

from playwright.async_api import async_playwright
import re
import asyncio
from datetime import datetime
from typing import List, Dict
from .base_scraper import BaseScraper
from .job_schema import get_job_dict


class SignatureAviationScraper(BaseScraper):
    """Scraper for Signature Aviation job postings"""

    def __init__(self, config: dict, db_manager=None):
        super().__init__(config, "signature", db_manager=db_manager)
        self.api_url = self.site_config.get("api_url", "")
        self.site_number = self.site_config.get("site_number", "CX_1")

    async def fetch_jobs_from_api(self) -> List[Dict]:
        """Fetch basic job data from Oracle Cloud API"""
        all_jobs = []
        offset = 0
        page_count = 0

        print("Fetching jobs from API (with TLS fingerprinting)...")

        while True:
            if self.max_pages and page_count >= self.max_pages:
                print(f"Reached max pages limit: {self.max_pages}")
                break
            if self.max_jobs and len(all_jobs) >= self.max_jobs:
                print(f"Reached max jobs limit: {self.max_jobs}")
                break
            print(f"  Fetching page {page_count + 1} (offset {offset})...")
            params = {
                "onlyData": "true",
                "expand": "requisitionList.workLocation,requisitionList.otherWorkLocations",
                "finder": f"findReqs;siteNumber={self.site_number},facetsList=LOCATIONS;WORK_LOCATIONS;WORKPLACE_TYPES;TITLES;CATEGORIES;ORGANIZATIONS;POSTING_DATES;FLEX_FIELDS,limit=25,sortBy=POSTING_DATES_DESC,offset={offset}",
            }
            try:
                # Use the new async make_request from BaseScraper
                response = await self.make_request(
                    self.api_url,
                    params=params,
                    headers={"Accept": "application/json"},
                    timeout=30,
                )

                data = response.json()
                items = data.get("items", [])
                if not items:
                    break
                jobs = items[0].get("requisitionList", [])
                if not jobs:
                    break
                for job in jobs:
                    if self.max_jobs and len(all_jobs) >= self.max_jobs:
                        break
                    all_jobs.append(get_job_dict(**self._extract_job_data(job)))
                print(f"    Found {len(jobs)} jobs (total: {len(all_jobs)})")
                if len(jobs) < 25:
                    print("  Last page reached")
                    break
                offset += 25
                page_count += 1
            except Exception as e:
                print(f"  Error fetching page: {e}")
                break
        return all_jobs

    def _extract_job_data(self, job: Dict) -> Dict:
        """Extract relevant fields from API job data"""
        job_id = str(job.get("Id", ""))

        # Parse posted date
        posted_date_raw = job.get("PostedDate", "")
        posted_date = self.parse_posted_date(posted_date_raw) if posted_date_raw else ""

        # Parse closing date
        closing_date_raw = job.get("PostingEndDate", "")
        closing_date = (
            self.parse_posted_date(closing_date_raw) if closing_date_raw else ""
        )

        return {
            "job_id": job_id,
            "title": job.get("Title", ""),
            "company": self.company_name,
            "source": self.site_key,
            "url": f"{self.base_url}/en/sites/{self.site_number}/job/{job_id}",
            "apply_url": f"{self.base_url}/en/sites/{self.site_number}/job/{job_id}",
            "location": self.normalize_location(job.get("PrimaryLocation", "")),
            "job_type": job.get("WorkplaceType", ""),
            "department": job.get("Organization", ""),
            "posted_date": posted_date,
            "closing_date": closing_date,
            "timestamp": datetime.now().isoformat(),
        }

    async def fetch_job_descriptions(self, jobs: List[Dict]) -> List[Dict]:
        """Fetch detailed descriptions from job pages using Playwright"""

        print(f"\nExtracting descriptions for {len(jobs)} jobs...")
        print(f"Processing in batches of {self.batch_size}...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            for i in range(0, len(jobs), self.batch_size):
                batch = jobs[i : i + self.batch_size]
                print(
                    f"\nBatch {i // self.batch_size + 1}/{(len(jobs) - 1) // self.batch_size + 1} (jobs {i + 1}-{min(i + self.batch_size, len(jobs))})"
                )

                tasks = [self._extract_description(browser, job) for job in batch]
                await asyncio.gather(*tasks, return_exceptions=True)

                completed = sum(1 for job in jobs if job.get("description"))
                print(f"  Progress: {completed}/{len(jobs)} complete")

                await self.random_delay(0.5, 1.0)

            await browser.close()

        return jobs

    async def _extract_description(self, browser, job: Dict):
        """Extract description for a single job"""

        page, context = await self.setup_stealth_page(browser)

        try:
            await self.random_delay(1, 2)
            await page.goto(job["url"], wait_until="networkidle", timeout=30000)
            await self.random_delay(2, 4)
            await self.simulate_human_behavior(page)

            # Extract description
            desc_elem = await page.query_selector(".job-details__description-content")
            if desc_elem:
                desc_html = await desc_elem.inner_html()
                description = re.sub(r"<[^>]+>", " ", desc_html)
                description = re.sub(r"\s+", " ", description).strip()
                job["description"] = description
            else:
                job["description"] = ""

            job["requirements"] = ""
            job["qualifications"] = ""

        except Exception as e:
            print(f"    Error extracting {job['job_id']}: {str(e)[:50]}")
            job["description"] = ""
            job["requirements"] = ""
            job["qualifications"] = ""
        finally:
            await page.close()
            await context.close()

    async def run(self):
        """Main execution method"""
        self.print_header()

        # Step 1: Fetch from API
        jobs = await self.fetch_jobs_from_api()

        if not jobs:
            print("No jobs found!")
            return []

        print(f"\n✓ Fetched {len(jobs)} jobs from API")

        # Step 2: Apply title filtering BEFORE fetching descriptions
        if self.use_filter and self.filter_manager:
            print("\n🔍 Applying title filter...")
            matched_jobs, rejected_jobs, filter_stats = self.apply_title_filter(jobs)

            self.filter_manager.print_filter_stats(filter_stats)

            if not matched_jobs:
                print("❌ No jobs matched the filter criteria")
                return []

            print(
                f"✓ {len(matched_jobs)} jobs matched filter (will fetch descriptions)"
            )
            print(f"✗ {len(rejected_jobs)} jobs rejected (not relevant)")
            jobs = matched_jobs

        # Step 3: Filter duplicates
        jobs, duplicate_count = await self.filter_new_jobs(jobs)
        if duplicate_count > 0:
            print(f"\n🔄 Filtered out {duplicate_count} duplicate jobs")

        # Step 4: Fetch descriptions
        jobs = await self.fetch_job_descriptions(jobs)

        # Step 5: Save results
        await self.save_results(jobs)

        # Show sample
        self.print_sample(jobs)

        return jobs
