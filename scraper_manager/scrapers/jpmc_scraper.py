import asyncio
from datetime import datetime
from typing import List, Dict
import re
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

class JpmcScraper(BaseScraper):
    """Scraper for JPMorgan Chase (JPMC) Oracle Cloud HCM job postings"""

    def __init__(self, config: dict, db_manager=None, site_key="jpmc"):
        super().__init__(config, site_key, db_manager=db_manager)
        self.site_config = config.get("sites", {}).get(site_key, {})
        self.base_url = self.site_config.get("base_url", "https://jpmc.fa.oraclecloud.com")
        self.api_url = self.site_config.get(
            "api_url",
            f"{self.base_url}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
        )
        self.site_number = self.site_config.get("site_number", "CX_1001")
        self.search_keyword = self.site_config.get("search_keyword", "dispatcher" if site_key == "jpmc" else "")
        self.company_name = self.site_config.get("company_name", "JPMorgan Chase")

    async def fetch_jobs_from_api(self) -> List[Dict]:
        """Fetch basic job data from Oracle Cloud API"""
        all_jobs = []
        offset = 0
        page_count = 0

        print(f"Fetching JPMC jobs from API...")

        while True:
            if self.max_pages and page_count >= self.max_pages:
                print(f"Reached max pages limit: {self.max_pages}")
                break
            if self.max_jobs and len(all_jobs) >= self.max_jobs:
                print(f"Reached max jobs limit: {self.max_jobs}")
                break
            
            print(f"  Fetching page {page_count + 1} (offset {offset})...")
            
            finder_str = f"findReqs;siteNumber={self.site_number}"
            if getattr(self, "search_keyword", None):
                finder_str += f",keyword={self.search_keyword}"
            finder_str += f",facetsList=LOCATIONS;WORK_LOCATIONS;WORKPLACE_TYPES;TITLES;CATEGORIES;ORGANIZATIONS;POSTING_DATES;FLEX_FIELDS,limit=25,sortBy=POSTING_DATES_DESC,offset={offset}"

            params = {
                "onlyData": "true",
                "expand": "requisitionList.workLocation,requisitionList.otherWorkLocations",
                "finder": finder_str,
            }
            
            try:
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
                    all_jobs.append(self._extract_job_data(job))
                
                print(f"    Found {len(jobs)} jobs (total parsed: {len(all_jobs)})")
                if len(jobs) < 25:
                    print("  Last page reached")
                    break
                
                offset += 25
                page_count += 1
                await asyncio.sleep(1) # Polite delay
                
            except Exception as e:
                print(f"  Error fetching page from Oracle API: {e}")
                break
                
        return all_jobs

    def _extract_job_data(self, job: Dict) -> Dict:
        """Extract relevant fields from API job data"""
        job_id = str(job.get("Id", ""))

        posted_date_raw = job.get("PostedDate", "")
        posted_date = self.parse_posted_date(posted_date_raw) if posted_date_raw else ""

        closing_date_raw = job.get("PostingEndDate", "")
        closing_date = (
            self.parse_posted_date(closing_date_raw) if closing_date_raw else ""
        )

        return {
            "job_id": f"{self.site_key}_{job_id}",
            "title": job.get("Title", ""),
            "company": self.company_name,
            "source": self.site_key,
            "url": f"{self.base_url}/hcmUI/CandidateExperience/en/sites/{self.site_number}/job/{job_id}",
            "apply_url": f"{self.base_url}/hcmUI/CandidateExperience/en/sites/{self.site_number}/job/{job_id}",
            "location": self.normalize_location(job.get("PrimaryLocation", "")),
            "job_type": job.get("WorkplaceType", ""),
            "department": job.get("Organization", ""),
            "posted_date": posted_date,
            "closing_date": closing_date,
            "timestamp": datetime.now().isoformat(),
            "description": "",
            "requirements": "",
            "qualifications": "",
        }

    async def fetch_job_descriptions(self, jobs: List[Dict]) -> List[Dict]:
        """Fetch detailed descriptions from job pages using Playwright"""
        print(f"\nExtracting descriptions for {len(jobs)} jobs...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)

            for i in range(0, len(jobs), self.batch_size):
                batch = jobs[i : i + self.batch_size]
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
            await page.goto(job["url"], wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)

            # Query specifically for description content
            desc_elem = await page.query_selector(".job-details__description-content")
            if desc_elem:
                desc_html = await desc_elem.inner_html()
                description = re.sub(r"<[^>]+>", " ", desc_html)
                description = re.sub(r"\s+", " ", description).strip()
                job["description"] = description
                # Backfill location from the original posting when missing.
                if not job.get("location") or job.get("location") == "Unknown":
                    _loc = await self.extract_location_from_page(page)
                    if _loc:
                        job["location"] = _loc
            else:
                job["description"] = ""

        except Exception as e:
            print(f"    Error extracting description for {job['job_id']}: {e}")
            job["description"] = ""
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

        # Programmatically filter JPMC jobs to only "Flight Dispatcher"
        if self.site_key == "jpmc":
            jobs = [j for j in jobs if j.get("title", "").strip().lower() == "flight dispatcher"]
            print(f"✓ Filtered to 'Flight Dispatcher' only: {len(jobs)} jobs remaining")

        # Step 2: Apply title filtering BEFORE fetching descriptions
        if self.use_filter and self.filter_manager:
            print("\n🔍 Applying title filter...")
            matched_jobs, rejected_jobs, filter_stats = self.apply_title_filter([get_job_dict(**j) for j in jobs])
            self.filter_manager.print_filter_stats(filter_stats)

            if not matched_jobs:
                print("❌ No jobs matched the filter criteria")
                return []

            print(f"✓ {len(matched_jobs)} jobs matched filter (will fetch descriptions)")
            print(f"✗ {len(rejected_jobs)} jobs rejected (not relevant)")
            jobs = matched_jobs
        else:
            jobs = [get_job_dict(**j) for j in jobs]

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
