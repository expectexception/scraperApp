"""
Flygosh Jobs Scraper
Extracts aviation jobs from flygoshjobs.com
"""

from playwright.async_api import async_playwright
import re
import asyncio
from datetime import datetime
from typing import List, Dict
from .base_scraper import BaseScraper
import logging

logger = logging.getLogger(__name__)


class FlygoshScraper(BaseScraper):
    """Scraper for Flygosh aviation job postings"""

    def __init__(self, config: dict, db_manager=None):
        super().__init__(config, "flygosh", db_manager=db_manager)
        self.jobs_url = self.site_config.get("jobs_url", "")

    async def fetch_jobs_from_listing(self) -> List[Dict]:
        """Fetch job listings from the main jobs page using Playwright"""
        all_jobs = []

        logger.info("Fetching jobs from listing page (JavaScript-rendered)...")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                page, context = await self.setup_stealth_page(browser)

                await self.random_delay(1, 2)
                await page.goto(self.jobs_url, wait_until="networkidle", timeout=30000)
                await self.random_delay(2, 4)
                await self.simulate_human_behavior(page)

                # Find job cards - update selector based on inspection
                job_cards = await page.query_selector_all('div[class*="job-card"]')

                logger.info(f"  Found {len(job_cards)} job cards")

                for idx, card in enumerate(job_cards):
                    if self.max_jobs and len(all_jobs) >= self.max_jobs:
                        break

                    try:
                        # SuccessFactors/Next.js/etc layout update
                        # Use more specific selectors based on inspection
                        title_el = await card.query_selector(
                            ".fg-job-title a, .job-title a, h3 a, h4 a"
                        )
                        if not title_el:
                            title_el = await card.query_selector(
                                'a[href*="/job/"]:not(:empty)'
                            )

                        if not title_el:
                            # Final fallback: any link with /job/ and try to get text from card if link is empty
                            title_el = await card.query_selector('a[href*="/job/"]')

                        url = await title_el.get_attribute("href") if title_el else None
                        title = await title_el.text_content() if title_el else None

                        if not title or not title.strip():
                            # If individual link is empty, try the whole card text or specific title div
                            title_div = await card.query_selector(
                                ".fg-job-title, .job-title, h3, h4"
                            )
                            if title_div:
                                title = await title_div.text_content()

                        if not url:
                            continue

                        if not url.startswith("http"):
                            url = (
                                self.base_url + url
                                if url.startswith("/")
                                else f"{self.base_url}/{url}"
                            )

                        # Extract Company from company link
                        company_el = await card.query_selector(
                            'a[href*="/company-jobs/"]'
                        )
                        company = (
                            await company_el.inner_text()
                            if company_el
                            else self.company_name
                        )

                        # Extract Location (try to parse from text if no specific selector)
                        # Text usually looks like: "Senior First Officer \n United Arab Emirates | Emirates"
                        all_text = await card.inner_text()
                        location = "Unknown"

                        # Simple heuristic: text between title and company or just check for |
                        if "|" in all_text:
                            all_text.split("|")
                            # parts[0] likely contains location at the end
                            # Let's try to capture the line before the pipe
                            lines = all_text.split("\n")
                            for line in lines:
                                if "|" in line:
                                    loc_part = line.split("|")[0].strip()
                                    if loc_part:
                                        location = loc_part
                                    break

                        all_jobs.append(
                            {
                                "job_id": f"flygosh-{idx + 1}-{datetime.now().timestamp()}",
                                "title": title.strip(),
                                "company": company.strip(),
                                "source": self.site_key,
                                "url": url,
                                "apply_url": url,
                                "location": location,
                                "job_type": "",
                                "department": "",
                                "posted_date": datetime.now().strftime("%Y-%m-%d"),
                                "timestamp": datetime.now().isoformat(),
                            }
                        )

                    except Exception as e:
                        print(f"    Error extracting card {idx}: {e}")
                        continue

                logger.info(f"  Extracted {len(all_jobs)} jobs")

                await context.close()
                await browser.close()

        except Exception as e:
            logger.error(f"  Error fetching jobs: {e}")

        return all_jobs

    async def _extract_job_from_card_playwright(self, card, idx: int) -> Dict:
        """Extract job data from a job card element using Playwright"""

        try:
            # Get full text
            text = await card.inner_text()
            lines = [line.strip() for line in text.split("\n") if line.strip()]

            # First line is usually the title
            title = lines[0] if lines else f"Job {idx + 1}"

            # Second line is often location | company
            location = ""
            company = ""
            if len(lines) > 1:
                location_line = lines[1]
                if "|" in location_line:
                    parts = location_line.split("|")
                    location = parts[0].strip()
                    if len(parts) > 1:
                        company = parts[1].strip()
                else:
                    location = location_line

            # Extract URL
            link = await card.query_selector("a[href]")
            url = ""
            if link:
                href = await link.get_attribute("href")
                if href:
                    if href.startswith("http"):
                        url = href
                    elif href.startswith("/"):
                        url = self.base_url + href
                    else:
                        url = f"{self.base_url}/{href}"

            return {
                "job_id": str(idx + 1),
                "title": title,
                "company": company or self.company_name,
                "source": self.site_key,
                "url": url,
                "apply_url": url,
                "location": location,
                "job_type": "",
                "department": "",
                "posted_date": "",
                "closing_date": "",
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"    Error extracting job card {idx}: {e}")
            return None

    async def fetch_job_descriptions(self, jobs: List[Dict]) -> List[Dict]:
        """Fetch detailed descriptions from job pages using Playwright"""

        logger.info(f"Extracting descriptions for {len(jobs)} jobs...")
        logger.info(f"Processing in batches of {self.batch_size}...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)

            for i in range(0, len(jobs), self.batch_size):
                batch = jobs[i : i + self.batch_size]
                logger.info(
                    f"Batch {i // self.batch_size + 1}/{(len(jobs) - 1) // self.batch_size + 1} (jobs {i + 1}-{min(i + self.batch_size, len(jobs))})"
                )

                tasks = [self._extract_description(browser, job) for job in batch]
                await asyncio.gather(*tasks, return_exceptions=True)

                completed = sum(1 for job in jobs if job.get("description"))
                logger.info(f"  Progress: {completed}/{len(jobs)} complete")

                await self.random_delay(0.5, 1.0)

            await browser.close()

        return jobs

    async def _extract_description(self, browser, job: Dict):
        """Extract full information from job detail page"""

        if not job.get("url"):
            job["description"] = ""
            job["requirements"] = ""
            job["qualifications"] = ""
            return

        page, context = await self.setup_stealth_page(browser)

        try:
            await self.random_delay(1, 2)
            await page.goto(job["url"], wait_until="networkidle", timeout=30000)
            await self.random_delay(2, 4)
            await self.simulate_human_behavior(page)

            # Get full page content
            await page.inner_text("body")

            # Extract job title (may be more complete on detail page)
            title_elem = await page.query_selector('h1, [class*="title"]')
            if title_elem:
                title = await title_elem.inner_text()
                if len(title) > len(job.get("title", "")):
                    job["title"] = title.strip()

            # Extract location (may be more specific)
            location_elem = await page.query_selector('[class*="location"], .location')
            if location_elem:
                location = await location_elem.inner_text()
                if location.strip():
                    job["location"] = location.strip()

            # Extract job type
            type_elem = await page.query_selector(
                '[class*="job-type"], [class*="employment"]'
            )
            if type_elem:
                job_type = await type_elem.inner_text()
                job["job_type"] = job_type.strip()

            # Extract posted date: first try JSON-LD JobPosting->datePosted, then date/time elements
            parsed_date = None
            try:
                scripts = await page.query_selector_all(
                    'script[type="application/ld+json"]'
                )
                for s in scripts:
                    try:
                        json_text = await s.inner_text()
                        import json as _json

                        data = _json.loads(json_text)
                        items = data if isinstance(data, list) else [data]
                        for item in items:
                            if isinstance(item, dict) and (
                                item.get("@type") and "JobPosting" in item.get("@type")
                            ):
                                if item.get("datePosted"):
                                    parsed_date = self.parse_posted_date(
                                        item.get("datePosted")
                                    )
                                    if parsed_date:
                                        job["posted_date"] = parsed_date
                                        break
                        if parsed_date:
                            break
                    except Exception:
                        continue
            except Exception:
                pass

            if not parsed_date:
                date_elem = await page.query_selector(
                    '[class*="date"], time, [class*="posted"]'
                )
                if date_elem:
                    date_text = await date_elem.inner_text()
                    parsed_date = self.parse_posted_date(date_text.strip())
                    job["posted_date"] = (
                        parsed_date if parsed_date else date_text.strip()
                    )
            # Fallback posted_date if still not found
            if not job.get("posted_date"):
                fallback_date = await self.extract_posted_date_from_page(page)
                if fallback_date:
                    job["posted_date"] = fallback_date

            # Extract full description
            desc_selectors = [
                ".job-description",
                '[class*="description"]',
                ".description",
                ".content",
                "article",
                "main",
            ]

            description = ""
            for selector in desc_selectors:
                desc_elem = await page.query_selector(selector)
                if desc_elem:
                    desc_html = await desc_elem.inner_html()
                    description = re.sub(r"<[^>]+>", " ", desc_html)
                    description = re.sub(r"\s+", " ", description).strip()
                    if len(description) > 100:  # Valid description
                        break

            job["description"] = description
            # Fallback description: if not valid, try base scraper heuristic
            if not job["description"] or len(job["description"]) < 80:
                fallback_desc = await self.extract_description_from_page(page)
                if fallback_desc and len(fallback_desc) > len(job["description"] or ""):
                    job["description"] = fallback_desc

            # Extract requirements section
            requirements = ""
            req_keywords = ["requirement", "qualification", "skill", "experience"]
            for keyword in req_keywords:
                req_elem = await page.query_selector(
                    f'[class*="{keyword}"], [id*="{keyword}"]'
                )
                if req_elem:
                    req_html = await req_elem.inner_html()
                    requirements = re.sub(r"<[^>]+>", " ", req_html)
                    requirements = re.sub(r"\s+", " ", requirements).strip()
                    if len(requirements) > 50:
                        break

            job["requirements"] = requirements

            # Extract qualifications
            qual_elem = await page.query_selector('[class*="qualification"]')
            if qual_elem:
                qual_html = await qual_elem.inner_html()
                qualifications = re.sub(r"<[^>]+>", " ", qual_html)
                qualifications = re.sub(r"\s+", " ", qualifications).strip()
                job["qualifications"] = qualifications
            else:
                job["qualifications"] = ""

            # Extract salary
            salary_info = await self.extract_salary_from_page(page)
            job.update(salary_info)

        except Exception as e:
            logger.error(f"    Error extracting {job['job_id']}: {str(e)[:50]}")
            job["description"] = job.get("description", "")
            job["requirements"] = ""
            job["qualifications"] = ""
        finally:
            await page.close()
            await context.close()

    async def run(self):
        """Main execution method"""

        self.print_header()

        # Step 1: Fetch from listing page
        jobs = await self.fetch_jobs_from_listing()

        if not jobs:
            logger.warning("No jobs found!")
            return []

        logger.info(f"Fetched {len(jobs)} jobs from listing")

        # Step 2: Apply title filtering BEFORE fetching descriptions
        if self.use_filter and self.filter_manager:
            logger.info("Applying title filter...")
            matched_jobs, rejected_jobs, filter_stats = self.apply_title_filter(jobs)

            self.filter_manager.print_filter_stats(filter_stats)

            if not matched_jobs:
                logger.info("❌ No jobs matched the filter criteria")
                return []

            logger.info(
                f"✓ {len(matched_jobs)} jobs matched filter (will fetch descriptions)"
            )
            logger.info(f"✗ {len(rejected_jobs)} jobs rejected (not relevant)")
            jobs = matched_jobs

        # Step 3: Filter duplicates
        jobs, duplicate_count = await self.filter_new_jobs(jobs)
        if duplicate_count > 0:
            logger.info(f"Filtered out {duplicate_count} duplicate jobs")

        # Step 4: Fetch full details from each job page
        jobs = await self.fetch_job_descriptions(jobs)

        # Step 5: Save results
        await self.save_results(jobs)

        # Show sample
        self.print_sample(jobs)

        return jobs
