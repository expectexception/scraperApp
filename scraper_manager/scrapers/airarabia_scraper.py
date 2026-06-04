"""
Air Arabia Careers Scraper
Extracts aviation job listings from careers.airarabia.com
"""

import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
import re
import logging

logger = logging.getLogger(__name__)


class AirArabiaScraper(BaseScraper):
    """Scraper for Air Arabia Careers"""

    def __init__(self, config, db_manager=None, is_auh=False):
        site_key = "airarabia_auh" if is_auh else "airarabia"
        super().__init__(config, site_key, db_manager=db_manager)

        self.site_config = config.get("sites", {}).get(site_key, {})
        self.base_url = self.site_config.get(
            "base_url", "https://careers.airarabia.com"
        )
        self.jobs_url = self.site_config.get(
            "jobs_url", "https://careers.airarabia.com/search/"
        )
        self.company = "Air Arabia Abu Dhabi" if is_auh else "Air Arabia"
        self.source = "airarabia_auh" if is_auh else "airarabia"

    async def run(self):
        """Main execution method"""
        self.print_header()

        logger.info(f"Fetching jobs from {self.company_name}...")
        logger.info(f"URL: {self.jobs_url}")

        jobs = await self.fetch_jobs_from_listing()

        if not jobs:
            logger.warning("No jobs found")
            return []

        logger.info(f"Extracted {len(jobs)} jobs from listing")

        # Apply title filtering BEFORE fetching descriptions
        if self.use_filter and self.filter_manager:
            logger.info("Applying title filter...")
            matched_jobs, rejected_jobs, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

            if not matched_jobs:
                logger.warning("No jobs matched the filter criteria")
                return []
            jobs = matched_jobs

        # Filter duplicates
        jobs, duplicate_count = await self.filter_new_jobs(jobs)
        if duplicate_count > 0:
            logger.info(f"Filtered out {duplicate_count} duplicate jobs")

        # Fetch detailed descriptions
        jobs_with_descriptions = await self.fetch_job_descriptions(jobs)

        # Save results
        await self.save_results(jobs_with_descriptions)
        self.print_sample(jobs_with_descriptions)

        return jobs_with_descriptions

    async def fetch_jobs_from_listing(self):
        """Fetch jobs from Air Arabia listing page"""
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            page, context = await self.setup_stealth_page(browser)

            try:
                logger.info(f"Loading {self.company_name} careers page...")
                await self.random_delay(2, 4)
                await page.goto(
                    self.jobs_url, wait_until="domcontentloaded", timeout=40000
                )

                # Wait for dynamic content to load
                await self.random_delay(4, 7)
                await self.simulate_human_behavior(page)

                # Wait for the job list to render
                try:
                    await page.wait_for_selector("a.jobTitle-link", timeout=20000)
                except Exception:
                    logger.warning(
                        "Timed out waiting for a.jobTitle-link on Air Arabia"
                    )

                # Verified selector from live inspection of jobs.airarabiagroupcareers.com
                # Note: site has triplicate DOM entries per job (responsive layout).
                # Dedup by href to avoid counting the same job 3x.
                job_links = await page.query_selector_all("a.jobTitle-link")
                logger.info(
                    f"Found {len(job_links)} job link elements using verified selector: a.jobTitle-link"
                )

                if not job_links:
                    logger.warning(
                        "No job links found on Air Arabia. Page may not have rendered."
                    )

                # Extract job data from links
                added_urls = set()
                for link in job_links:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

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

                        if job_url in added_urls:
                            continue

                        # Extract title from link text
                        title = (await link.inner_text()).strip()
                        if not title or len(title) < 4:
                            continue

                        # Skip navigation/UI text (the site has triplicate DOM, so dedup by url+title)
                        skip_words = {
                            "apply now",
                            "log in",
                            "login",
                            "careers",
                            "home",
                            "search",
                            "sign up",
                            "register",
                        }
                        if title.lower() in skip_words:
                            continue

                        # Extract job ID
                        job_id = None
                        match = re.search(r"/job/(?:[^/]+/)?(\d+)", href)
                        if match:
                            job_id = match.group(1)
                        if not job_id:
                            job_id = f"{self.source}_{len(jobs) + 1}_{datetime.now().strftime('%Y%m%d')}"
                        else:
                            job_id = f"{self.source}_{job_id}"

                        job_data = {
                            "job_id": job_id,
                            "title": title,
                            "company": self.company,
                            "source": self.source,
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

                        # Attempt to get location / department if present in list
                        parent_handle = await link.evaluate_handle(
                            'el => el.closest("tr") || el.closest("li") || el.closest(".jobRow")'
                        )
                        parent = parent_handle.as_element()
                        if parent:
                            loc_elem = await parent.query_selector(
                                '.jobLocation, .location, [class*="location"]'
                            )
                            if loc_elem:
                                loc_text = await loc_elem.inner_text()
                                job_data["location"] = loc_text.strip()

                            date_elem = await parent.query_selector(
                                '.jobDate, .date, [class*="date"]'
                            )
                            if date_elem:
                                date_text = await date_elem.inner_text()
                                parsed = self.parse_posted_date(date_text)
                                job_data["posted_date"] = (
                                    parsed if parsed else date_text.strip()
                                )

                            dept_elem = await parent.query_selector(
                                '.jobDepartment, .department, [class*="department"]'
                            )
                            if dept_elem:
                                dept_text = await dept_elem.inner_text()
                                job_data["department"] = dept_text.strip()

                        jobs.append(job_data)
                        added_urls.add(job_url)

                    except Exception as e:
                        logger.error(f"Error parsing link: {e}")
                        continue

            except asyncio.TimeoutError:
                logger.error("Timeout loading page")
            except Exception as e:
                logger.error(f"Error fetching jobs: {e}")
            finally:
                await context.close()
                await browser.close()

        return jobs

    async def fetch_job_descriptions(self, jobs):
        """Fetch detailed descriptions for each job"""
        logger.info(f"Fetching detailed descriptions for {len(jobs)} jobs...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )

            for i in range(0, len(jobs), self.batch_size):
                batch = jobs[i : i + self.batch_size]
                tasks = []

                for job in batch:
                    if job.get("url"):
                        tasks.append(self._extract_description(browser, job))

                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

                logger.info(
                    f"  Processed {min(i + self.batch_size, len(jobs))}/{len(jobs)} jobs"
                )
                await asyncio.sleep(1)  # Extra cooling delay

            await browser.close()

        # Count jobs with descriptions
        with_desc = sum(1 for job in jobs if job.get("description"))
        logger.info(f"Successfully extracted {with_desc}/{len(jobs)} descriptions")

        return jobs

    async def _extract_description(self, browser, job):
        """Extract detailed description from job page"""
        try:
            page, context = await self.setup_stealth_page(browser)

            # Load job detail page
            await self.random_delay(1, 3)
            await page.goto(job["url"], wait_until="load", timeout=30000)
            await self.random_delay(2, 4)
            await self.simulate_human_behavior(page)

            # Description selectors
            desc_selectors = [
                "#jobDescription",
                ".job-description",
                ".jobdescription",
                '[itemprop="description"]',
                ".content",
                "article",
                "main",
                ".job-details",
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

            # Fallback
            if not description or len(description) < 100:
                try:
                    fallback_desc = await self.extract_description_from_page(page)
                    if fallback_desc and len(fallback_desc) > len(description):
                        description = fallback_desc
                except Exception:
                    pass

            job["description"] = description

            # Fetch location specifically if not found
            if not job.get("location"):
                loc_selectors = [
                    ".jobLocation",
                    'span[itemprop="jobLocation"]',
                    ".location",
                ]
                for ls in loc_selectors:
                    elem = await page.query_selector(ls)
                    if elem:
                        ltext = await elem.inner_text()
                        job["location"] = ltext.strip()
                        break

            # Fetch date if not found
            if not job.get("posted_date"):
                date_selectors = [".jobDate", 'span[itemprop="datePosted"]', ".date"]
                for ds in date_selectors:
                    elem = await page.query_selector(ds)
                    if elem:
                        dtext = await elem.inner_text()
                        parsed = self.parse_posted_date(dtext)
                        job["posted_date"] = parsed if parsed else dtext.strip()
                        break

            # Date fallback
            if not job.get("posted_date"):
                date = await self.extract_posted_date_from_page(page)
                if date:
                    job["posted_date"] = date

            await page.close()
            await context.close()

        except asyncio.TimeoutError:
            logger.warning(f"Timeout for {job['job_id']}")
        except Exception as e:
            logger.error(f"Error fetching description for {job['job_id']}: {e}")
