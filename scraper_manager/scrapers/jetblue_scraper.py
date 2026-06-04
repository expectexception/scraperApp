"""
JetBlue Careers Scraper
Extracts aviation job listings from careers.jetblue.com (SuccessFactors)
"""

import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict
import re


class JetBlueScraper(BaseScraper):
    """Scraper for JetBlue Careers (SuccessFactors)"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, "jetblue", db_manager=db_manager)
        self.site_config = config.get("sites", {}).get("jetblue", {})
        self.base_url = self.site_config.get("base_url", "https://careers.jetblue.com")
        self.jobs_url = self.site_config.get(
            "jobs_url",
            "https://careers.jetblue.com/search/?createNewAlert=false&q=&locationsearch=",
        )

    async def run(self):
        """Main execution method"""
        self.print_header()

        print(
            f"Fetching jobs from {self.site_config.get('name', 'JetBlue Airways')}..."
        )
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

            # print(f"DEBUG: filter_stats keys: {filter_stats.keys()}") # Debug info if needed

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
        """Fetch jobs from SuccessFactors listing page with pagination"""
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                # SuccessFactors typically allows startrow pagination
                # We'll crawl a few pages if needed
                for start_row in range(0, 500, 25):  # 25 results per page
                    current_url = f"{self.jobs_url}&startrow={start_row}"
                    print(f"Loading JetBlue careers page (startrow={start_row})...")

                    await page.goto(
                        current_url, wait_until="domcontentloaded", timeout=30000
                    )
                    await self.random_delay(3, 5)
                    await self.simulate_human_behavior(page)

                    # Wait for job rows
                    try:
                        await page.wait_for_selector("tr.data-row", timeout=15000)
                    except Exception:
                        if start_row == 0:
                            print("⚠️  Timed out waiting for tr.data-row on JetBlue")
                        else:
                            print(f"ℹ️  No more results found at startrow={start_row}")
                        break

                    rows = await page.query_selector_all("tr.data-row")
                    if not rows:
                        break

                    print(f"✓ Found {len(rows)} job rows on this page")

                    for row in rows:
                        try:
                            # Extract title and link
                            link_elem = await row.query_selector("a.jobTitle-link")
                            if not link_elem:
                                continue

                            title = (await link_elem.inner_text()).strip()
                            href = await link_elem.get_attribute("href")

                            if not href or not title:
                                continue

                            # Build full URL
                            if href.startswith("/"):
                                job_url = f"{self.base_url}{href}"
                            elif href.startswith("http"):
                                job_url = href
                            else:
                                job_url = f"{self.base_url}/{href}"

                            # Extract location
                            loc_elem = await row.query_selector("span.jobLocation")
                            location = (
                                (await loc_elem.inner_text()).strip()
                                if loc_elem
                                else "Unknown"
                            )

                            # Extract Job ID / Req ID
                            req_elem = await row.query_selector("span.jobFacility")
                            req_id = (
                                (await req_elem.inner_text()).strip()
                                if req_elem
                                else None
                            )

                            if not req_id and "jobId=" in href:
                                match = re.search(r"jobId=(\d+)", href)
                                if match:
                                    req_id = match.group(1)

                            if not req_id:
                                # Fallback ID from URL hash or something
                                req_id = f"jb_{len(jobs) + 1}"

                            job_data = {
                                "job_id": f"jetblue_{req_id}",
                                "title": title,
                                "company": "JetBlue",
                                "source": self.site_key,
                                "url": job_url,
                                "apply_url": job_url,
                                "location": self.normalize_location(location),
                                "job_type": "",
                                "department": "",
                                "posted_date": "",
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

                    # Check if there's a "Next" page or if we've reached the end
                    # SuccessFactors often shows "next" or we just check if we got fewer than 25 results
                    if len(rows) < 25:
                        break

            except Exception as e:
                print(f"❌ Error fetching jobs: {e}")
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
        """Extract detailed description from SuccessFactors job page"""
        try:
            page, context = await self.setup_stealth_page(browser)

            # Load job detail page
            await page.goto(job["url"], wait_until="load", timeout=30000)
            await self.random_delay(2, 4)
            await self.simulate_human_behavior(page)

            # Extract description
            # SuccessFactors often uses .jobdescription or #job-description
            desc_selectors = [
                ".jobdescription",
                "#job-description",
                ".job-description",
                '[class*="description"]',
                ".content",
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
                # Fallback: Extract largest text block
                description = await self.extract_description_from_page(page)

            job["description"] = description

            # Extract posted date if available
            posted_date = await self.extract_posted_date_from_page(page)
            if posted_date:
                job["posted_date"] = posted_date

            await page.close()
            await context.close()

        except Exception:
            # print(f"  Error fetching description for {job['job_id']}: {e}")
            pass
