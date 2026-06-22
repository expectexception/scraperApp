"""
Royal Jet Careers Scraper
Extracts aviation job listings from careers.royaljetgroup.com
"""

import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict
import re
import logging

logger = logging.getLogger(__name__)


class RoyalJetScraper(BaseScraper):
    """Scraper for Royal Jet Careers"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, "royaljet", db_manager=db_manager)
        self.site_config = config.get("sites", {}).get("royaljet", {})
        self.base_url = self.site_config.get(
            "base_url", "https://careerroyaljet.talentera.com"
        )
        self.jobs_url = self.site_config.get(
            "jobs_url", "https://careerroyaljet.talentera.com/en/job-search-results/"
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

        # Fetch detailed descriptions
        jobs_with_descriptions = await self.fetch_job_descriptions(jobs)

        # Save results
        await self.save_results(jobs_with_descriptions)
        self.print_sample(jobs_with_descriptions)

        return jobs_with_descriptions

    async def fetch_jobs_from_listing(self):
        """Fetch jobs from Royal Jet listing page"""
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            page, context = await self.setup_stealth_page(browser)

            try:
                logger.info("Loading Royal Jet careers page...")
                await self.random_delay(2, 4)
                await page.goto(
                    self.jobs_url, wait_until="domcontentloaded", timeout=40000
                )

                # Wait for dynamic content to load
                await self.random_delay(4, 7)
                await self.simulate_human_behavior(page)

                # Wait for Talentera dynamic content to load
                try:
                    await page.wait_for_selector("a.text-snip", timeout=20000)
                except Exception:
                    logger.warning("Timed out waiting for a.text-snip on Royal Jet")

                # Verified selector from live inspection of careerroyaljet.talentera.com
                # 'a.text-snip' is exclusively used for actual job title links.
                job_links = await page.query_selector_all("a.text-snip")
                logger.info(
                    f"Found {len(job_links)} jobs using verified selector: a.text-snip"
                )

                if not job_links:
                    logger.warning(
                        "No job links found with verified selector for Royal Jet."
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

                        # Build full URL (Talentera uses relative paths like /en/uae/jobs/title-id/)
                        if href.startswith("/"):
                            job_url = f"https://careerroyaljet.talentera.com{href}"
                        elif href.startswith("http"):
                            job_url = href
                        else:
                            job_url = f"https://careerroyaljet.talentera.com/{href}"

                        if job_url in added_urls:
                            continue

                        # Extract title from link text
                        title = (await link.inner_text()).strip()
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
                            "jobs",
                        }
                        if title.lower() in skip_words:
                            continue

                        # Extract job ID
                        job_id = None
                        match = re.search(r"[-/](\d{3,})(?:[-/]|$)", href)
                        if match:
                            job_id = match.group(1)
                        if not job_id:
                            job_id = f"royaljet_{len(jobs) + 1}_{datetime.now().strftime('%Y%m%d')}"
                        else:
                            job_id = f"royaljet_{job_id}"

                        job_data = get_job_dict(
                            job_id=job_id,
                            title=title,
                            company="Royal Jet",
                            location="Abu Dhabi, UAE",
                            url=job_url,
                            source_url=job_url,
                            description="",
                            apply_url=job_url,
                            posted_date="",
                            source="royaljet",
                        )

                        # Find container and extract extra info (location, date)
                        parent_handle = await link.evaluate_handle(
                            'el => el.closest("tr") || el.closest("li") || el.closest(".job")'
                        )
                        parent = parent_handle.as_element()
                        if parent:
                            loc_elem = await parent.query_selector(
                                '.location, [class*="location"]'
                            )
                            if loc_elem:
                                loc_text = await loc_elem.inner_text()
                                job_data["location"] = loc_text.strip()

                            date_elem = await parent.query_selector(
                                '.date, [class*="date"]'
                            )
                            if date_elem:
                                date_text = await date_elem.inner_text()
                                parsed = self.parse_posted_date(date_text)
                                job_data["posted_date"] = (
                                    parsed if parsed else date_text.strip()
                                )

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

            # Common Talentera/Job detail selectors
            desc_selectors = [
                "#job-description",
                ".job-description",
                ".job-details",
                '[itemprop="description"]',
                ".content",
                "article",
                "main",
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
