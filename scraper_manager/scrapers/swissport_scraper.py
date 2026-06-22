"""
Swissport Careers Scraper
Extracts aviation job listings from careers.swissport.com (iCIMS/Angular Platform)
"""

import asyncio
import re
from datetime import datetime
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict


class SwissportScraper(BaseScraper):
    """Scraper for Swissport Careers"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, "swissport", db_manager=db_manager)
        self.site_config = config.get("sites", {}).get("swissport", {})
        self.base_url = self.site_config.get(
            "base_url", "https://careers.swissport.com"
        )
        self.jobs_url = self.site_config.get(
            "jobs_url", "https://careers.swissport.com/jobs?sortBy=relevance&page=1"
        )

    async def run(self):
        """Main execution method"""
        self.print_header()

        print(f"Fetching jobs from {self.company_name}...")

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
        """Fetch job listings across multiple pages"""
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                for p_num in range(1, self.max_pages + 1):
                    if "page=" in self.jobs_url:
                        current_url = re.sub(r"page=\d+", f"page={p_num}", self.jobs_url)
                    else:
                        sep = "&" if "?" in self.jobs_url else "?"
                        current_url = f"{self.jobs_url}{sep}page={p_num}"
                    print(f"Loading page {p_num}: {current_url}")

                    await page.goto(
                        current_url, wait_until="networkidle", timeout=60000
                    )
                    await self.random_delay(3, 5)

                    # Wait for the listing to load
                    await page.wait_for_selector("a.job-title-link", timeout=20000)
                    await self.simulate_human_behavior(page)

                    # Get all job title links
                    job_elements = await page.query_selector_all("a.job-title-link")

                    if not job_elements:
                        print("⚠️ No job elements found on page")
                        break

                    for el in job_elements:
                        try:
                            title = (await el.inner_text()).strip()
                            href = await el.get_attribute("href")
                            if not href:
                                continue

                            job_url = (
                                f"{self.base_url}{href}"
                                if href.startswith("/")
                                else href
                            )

                            # Extract ID from URL /jobs/8486
                            job_id_match = re.search(r"/jobs/(\d+)", href)
                            job_id = (
                                job_id_match.group(1)
                                if job_id_match
                                else f"swp_{len(jobs) + 1}"
                            )

                            # Extract location from the panel (if possible without expanding,
                            # usually it's in a mat-panel-description)
                            location = "Global"
                            parent_panel = await el.evaluate_handle(
                                'el => el.closest("mat-expansion-panel")'
                            )
                            if parent_panel:
                                loc_el = await parent_panel.query_selector(
                                    ".location, mat-panel-description span"
                                )
                                if loc_el:
                                    loc_text = (await loc_el.inner_text()).strip()
                                    if loc_text:
                                        location = loc_text

                            job_data = {
                                "job_id": f"swissport_{job_id}",
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

                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    # Check if next page exists (optional but good)
                    # For Swissport, if we found jobs on current page, we try next
                    if len(job_elements) == 0:
                        break

            except Exception as e:
                print(f"❌ Error fetching Swissport listings: {e}")
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
        """Extract detailed description from Swissport job page"""
        try:
            page, context = await self.setup_stealth_page(browser)

            # Load job detail page
            await page.goto(job["url"], wait_until="networkidle", timeout=45000)
            await self.random_delay(2, 4)

            # Broad selector for description
            desc_selectors = [
                ".job-description",
                ".job-body",
                "#job-details",
                "mat-card-content",
                ".content",
                "main",
            ]

            description = ""
            for selector in desc_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        text = await elem.inner_text()
                        if text and len(text) > 300:
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
