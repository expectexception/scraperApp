"""
Falcon Aviation Services Careers Scraper
Extracts aviation job listings from falconaviation.ae
"""

import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
import logging

logger = logging.getLogger(__name__)


class FalconAviationScraper(BaseScraper):
    """Scraper for Falcon Aviation Services Careers"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, "falconaviation", db_manager=db_manager)
        self.site_config = config.get("sites", {}).get("falconaviation", {})
        self.base_url = self.site_config.get("base_url", "https://falconaviation.ae")
        self.jobs_url = self.site_config.get(
            "jobs_url", "https://falconaviation.ae/careers"
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

        # Save results (descriptions already extracted from accordion)
        await self.save_results(jobs)
        self.print_sample(jobs)

        return jobs

    async def fetch_jobs_from_listing(self):
        """Fetch jobs from Falcon Aviation listing page"""
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            page, context = await self.setup_stealth_page(browser)

            try:
                logger.info("Loading Falcon Aviation careers page...")
                await self.random_delay(2, 4)
                await page.goto(
                    self.jobs_url, wait_until="domcontentloaded", timeout=40000
                )

                # Wait for dynamic content to load
                await self.random_delay(4, 7)
                await self.simulate_human_behavior(page)

                # Wait for accordion to load
                try:
                    await page.wait_for_selector(
                        "button.accordion-button", timeout=20000
                    )
                except Exception:
                    logger.warning(
                        "Timed out waiting for accordion-button on Falcon Aviation"
                    )

                # Verified selector from live inspection: accordion buttons are job titles
                # Each button.accordion-button contains exactly one job title (40+ confirmed)
                job_links = await page.query_selector_all("button.accordion-button")
                logger.info(
                    f"Found {len(job_links)} accordion jobs using verified selector: button.accordion-button"
                )

                if not job_links:
                    logger.warning(
                        "No jobs found using the verified accordion button selector."
                    )
                    return []

                # Extract job data from links
                added_urls = set()
                for link in job_links:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    try:
                        # Extract title from accordion button
                        # Title may be direct text or inside a child span
                        title = (await link.inner_text()).strip()
                        if not title:
                            span = await link.query_selector("span, h3, h4")
                            if span:
                                title = (await span.inner_text()).strip()

                        if not title or len(title) < 4:
                            continue

                        # Skip navigation/UI text that might slip through
                        skip_words = {
                            "apply now",
                            "log in",
                            "login",
                            "careers",
                            "home",
                            "search",
                            "sign up",
                            "register",
                            "read more",
                            "view details",
                            "select",
                            "all open positions",
                            "general application",
                        }
                        if title.lower() in skip_words:
                            continue

                        # Falcon Aviation uses an accordion - job URL is the careers page
                        # since jobs don't have individual detail pages
                        job_url = self.jobs_url

                        if job_url in added_urls and job_url == self.jobs_url:
                            # Allow multiple jobs to share the careers URL (accordion style)
                            pass

                        # Extract job ID (accordion-based, use sequential ID)
                        job_id = f"falconaviation_{len(jobs) + 1}_{datetime.now().strftime('%Y%m%d')}"

                        job_data = {
                            "job_id": job_id,
                            "title": title,
                            "company": "Falcon Aviation Services",
                            "source": "falconaviation",
                            "url": job_url,
                            "apply_url": job_url,
                            "location": "Abu Dhabi, UAE",  # Headquartered in Abu Dhabi
                            "job_type": "",
                            "department": "",
                            "posted_date": "",
                            "closing_date": "",
                            "timestamp": datetime.now().isoformat(),
                            "description": "",
                            "requirements": "",
                            "qualifications": "",
                        }

                        # Try to extract the description from the accordion body
                        try:
                            parent = await link.evaluate_handle(
                                'el => el.closest(".accordion-item")'
                            )
                            if parent:
                                body = await parent.query_selector(".accordion-body")
                                if body:
                                    job_data["description"] = (
                                        await body.inner_text()
                                    ).strip()
                        except Exception as e:
                            logger.error(f"Error extracting accordion description: {e}")

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
                "#job-description",
                ".job-description",
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
            # Backfill location from the original posting when missing.
            if not job.get("location") or job.get("location") == "Unknown":
                _loc = await self.extract_location_from_page(page)
                if _loc:
                    job["location"] = _loc

            # Date attempt
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
