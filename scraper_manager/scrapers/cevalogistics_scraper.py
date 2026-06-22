import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict
import re

class CevaLogisticsScraper(BaseScraper):
    """Scraper for CEVA Logistics (SuccessFactors portal)."""

    def __init__(self, config, db_manager=None, site_key="cevalogistics"):
        super().__init__(config, site_key, db_manager=db_manager)
        self.site_config = config.get("sites", {}).get(site_key, {})
        self.base_url = self.site_config.get("base_url", "https://jobs.cmacgm-group.com")
        self.jobs_url = self.site_config.get(
            "jobs_url",
            "https://jobs.cmacgm-group.com/CEVALogistics/search/?createNewAlert=false&q=&locationsearch=&optionsFacetsDD_shifttype="
        )

    async def run(self):
        """Main execution method"""
        self.print_header()

        print(f"Fetching jobs from {self.site_config.get('name', 'CEVA Logistics')}...")
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
            self.filter_manager.print_filter_stats(filter_stats)

            if not matched_jobs:
                print("❌ No jobs matched the filter criteria")
                return []

            print(f"✓ {len(matched_jobs)} jobs matched filter (will fetch descriptions)")
            print(f"✗ {len(rejected_jobs)} jobs rejected (not relevant)")
            jobs = matched_jobs

        # Filter duplicates
        jobs, duplicate_count = await self.filter_new_jobs(jobs)
        if duplicate_count > 0:
            print(f"\n🔄 Filtered out {duplicate_count} duplicate jobs")

        # Fetch detailed descriptions
        jobs_with_descriptions = await self.fetch_job_descriptions(jobs)

        # Save results
        await self.save_results(jobs_with_descriptions)
        self.print_sample(jobs_with_descriptions)

        return jobs_with_descriptions

    async def fetch_jobs_from_listing(self):
        """Fetch jobs from SuccessFactors listing page"""
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                print("Loading CEVA Logistics careers page...")
                await page.goto(self.jobs_url, wait_until="domcontentloaded", timeout=40000)
                await page.wait_for_timeout(5000)

                # Wait for SuccessFactors selector
                try:
                    await page.wait_for_selector("a.jobTitle-link", timeout=20000)
                except Exception:
                    print("Warning: Timed out waiting for a.jobTitle-link")

                job_links = await page.query_selector_all("a.jobTitle-link")
                print(f"✓ Found {len(job_links)} jobs using selector a.jobTitle-link")

                if not job_links:
                    # Fallback to general /job/ URLs
                    job_links = [
                        el for el in await page.query_selector_all("a[href*='/job/']")
                        if (await el.inner_text()).strip()
                    ]
                    print(f"✓ Fallback: Found {len(job_links)} jobs using a[href*='/job/']")

                # Extract job data from links
                seen_urls = set()
                for link in job_links:
                    try:
                        href = await link.get_attribute("href")
                        if not href:
                            continue

                        # Build full URL
                        if href.startswith("/"):
                            job_url = f"{self.base_url}{href}"
                        elif href.startswith("http"):
                            job_url = href
                        else:
                            job_url = f"{self.base_url}/{href}"

                        if job_url in seen_urls:
                            continue
                        seen_urls.add(job_url)

                        # Extract title from link text
                        title = (await link.inner_text()).strip()
                        # Clean up carriage returns/newlines in title
                        title = title.replace("\n", " ").replace("\r", " ").strip()
                        if not title or len(title) < 5 or title.lower() in {"read more", "apply now"}:
                            continue

                        # Extract job ID from URL
                        job_id = None
                        match = re.search(r"/job/[^/]+/(\d+)/", job_url)
                        if match:
                            job_id = match.group(1)

                        if not job_id:
                            job_id = f"ceva_{hash(job_url)}"

                        job_data = {
                            "job_id": f"{self.site_key}_{job_id}",
                            "title": title,
                            "company": self.site_config.get("name", "CEVA Logistics"),
                            "source": self.site_key,
                            "url": job_url,
                            "apply_url": job_url,
                            "location": "",
                            "job_type": "",
                            "department": "",
                            "posted_date": "",
                            "closing_date": "",
                            "timestamp": datetime.now().isoformat(),
                            "description": "",
                            "requirements": "",
                            "qualifications": "",
                        }
                        jobs.append(job_data)

                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break

                    except Exception:
                        continue

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

                print(f"  Processed {min(i + self.batch_size, len(jobs))}/{len(jobs)} jobs")

            await browser.close()

        with_desc = sum(1 for job in jobs if job.get("description"))
        print(f"✓ Successfully extracted {with_desc}/{len(jobs)} descriptions")

        return jobs

    async def _extract_description(self, browser, job):
        """Extract detailed description from SuccessFactors job page"""
        try:
            page, context = await self.setup_stealth_page(browser)

            await page.goto(job["url"], wait_until="load", timeout=30000)
            await page.wait_for_timeout(3000)

            # Location extraction
            location_selectors = [
                "span.job-location",
                "li.job-location",
                ".job-location",
                "[data-location]",
                "span[itemprop='streetAddress']"
            ]

            for selector in location_selectors:
                try:
                    loc_elem = await page.query_selector(selector)
                    if loc_elem:
                        loc_text = await loc_elem.inner_text()
                        # Also check content attribute for meta tags
                        if not loc_text:
                            loc_text = await loc_elem.get_attribute("content")
                        if loc_text and len(loc_text) > 2:
                            job["location"] = loc_text.strip()
                            break
                except Exception:
                    continue

            # Fallback for location from URL
            if not job.get("location") or job["location"] == "Unknown":
                url_parts = job["url"].split("/")
                for part in url_parts:
                    if "job" in part.lower() or part.isdigit():
                        continue
                    if "-" in part:
                        potential_loc = part.split("-")[0]
                        if len(potential_loc) > 3:
                            job["location"] = potential_loc
                            break

            # Description extraction
            desc_selectors = [
                ".jobdescription",
                "#jobDescription",
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
                try:
                    fallback_desc = await self.extract_description_from_page(page)
                    if fallback_desc:
                        description = fallback_desc
                except Exception:
                    pass

            job["description"] = description
            # Backfill location from the original posting when missing.
            if not job.get("location") or job.get("location") == "Unknown":
                _loc = await self.extract_location_from_page(page)
                if _loc:
                    job["location"] = _loc

            # Date posted extraction
            try:
                posted_date = await self.extract_posted_date_from_page(page)
                if posted_date:
                    job["posted_date"] = posted_date
            except Exception:
                pass

            await page.close()
            await context.close()

        except Exception as e:
            print(f"  Error fetching description for {job['job_id']}: {e}")

class ChallengeGroupScraper(CevaLogisticsScraper):
    """Scraper for Challenge Group (SuccessFactors portal)."""
    def __init__(self, config, db_manager=None):
        super().__init__(config, db_manager=db_manager, site_key="challenge_group")
