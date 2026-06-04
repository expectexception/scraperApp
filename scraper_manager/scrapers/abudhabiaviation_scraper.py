"""
Abu Dhabi Aviation Scraper
Extracts aviation job listings from www.ada.ae/careers
"""

import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
import logging

logger = logging.getLogger(__name__)


class AbuDhabiAviationScraper(BaseScraper):
    """Scraper for Abu Dhabi Aviation Careers"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, "abudhabiaviation", db_manager=db_manager)
        self.site_config = config.get("sites", {}).get("abudhabiaviation", {})
        self.base_url = self.site_config.get("base_url", "https://ada.ae")
        self.jobs_url = self.site_config.get(
            "jobs_url", "https://ada.ae/general-application/"
        )

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

        # Save results (descriptions extracted on main page for ADA)
        await self.save_results(jobs)
        self.print_sample(jobs)

        return jobs

    async def fetch_jobs_from_listing(self):
        """Fetch jobs from ADA listing page"""
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            page, context = await self.setup_stealth_page(browser)

            try:
                # ADA often lists roles directly on the careers page or provides a general email.
                logger.info("Loading Abu Dhabi Aviation careers page...")
                await self.random_delay(2, 4)
                await page.goto(
                    self.jobs_url, wait_until="domcontentloaded", timeout=40000
                )

                # Wait for dynamic content to load
                await self.random_delay(4, 7)
                await self.simulate_human_behavior(page)

                # Attempt to extract job postings if they are listed as accordions, divs, or list items
                selectors = [
                    ".career-item",
                    ".job-post",
                    ".accordion-item",
                    ".job-listing",
                    "li.job",
                ]
                job_elements = []
                for selector in selectors:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        job_elements = elements
                        break

                if job_elements:
                    for idx, el in enumerate(job_elements):
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break

                        try:
                            # Attempt to find title
                            title_el = await el.query_selector(
                                "h3, h4, h5, .title, .job-title, a"
                            )
                            if not title_el:
                                continue
                            title = (await title_el.inner_text()).strip()

                            if len(title) < 5:
                                continue

                            # Attempt to find description
                            desc_el = await el.query_selector(
                                ".description, .content, .job-content, p"
                            )
                            description = ""
                            if desc_el:
                                description = (await desc_el.inner_text()).strip()

                            job_id = f"abudhabiaviation_{idx + 1}_{datetime.now().strftime('%Y%m%d')}"

                            job_data = {
                                "job_id": job_id,
                                "title": title,
                                "company": "Abu Dhabi Aviation",
                                "source": "abudhabiaviation",
                                "url": self.jobs_url,
                                "apply_url": "mailto:careers@abudhabiaviation.com",  # Standard for ADA
                                "location": "Abu Dhabi, UAE",
                                "job_type": "",
                                "department": "",
                                "posted_date": "",
                                "closing_date": "",
                                "timestamp": datetime.now().isoformat(),
                                "description": description,
                                "requirements": "",
                                "qualifications": "",
                            }
                            jobs.append(job_data)
                        except Exception:
                            continue

                else:
                    # If specific containers are not found, fallback to scanning text for roles
                    logger.info(
                        "No structured job elements found, scanning page text..."
                    )
                    body_text = await page.inner_text("body")
                    # Look for keywords like "seeking", "hiring", "positions for"
                    # Often if they don't have open positions they say "Please email careers@..."
                    if (
                        "careers@abudhabiaviation.com" in body_text.lower()
                        or "hr@abudhabiaviation.com" in body_text.lower()
                    ):
                        # We'll create a general "Open Application" job to capture the general recruitment intent
                        job_data = {
                            "job_id": f"abudhabiaviation_general_{datetime.now().strftime('%Y%m%d')}",
                            "title": "General Open Application / Talent Pool",
                            "company": "Abu Dhabi Aviation",
                            "source": "abudhabiaviation",
                            "url": self.jobs_url,
                            "apply_url": "mailto:careers@abudhabiaviation.com",
                            "location": "Abu Dhabi, UAE",
                            "job_type": "Full-time",
                            "department": "Various",
                            "posted_date": datetime.now().date().isoformat(),
                            "closing_date": "",
                            "timestamp": datetime.now().isoformat(),
                            "description": "Abu Dhabi Aviation is always looking for talented individuals. Please visit the careers page to view potential roles or submit your CV to the careers email address.",
                            "requirements": "",
                            "qualifications": "",
                        }
                        jobs.append(job_data)

            except asyncio.TimeoutError:
                logger.error("Timeout loading page")
            except Exception as e:
                logger.error(f"Error fetching jobs: {e}")
            finally:
                await context.close()
                await browser.close()

        return jobs
