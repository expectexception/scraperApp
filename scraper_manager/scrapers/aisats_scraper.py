"""
AISATS Careers Scraper
Extracts aviation job listings from www.aisats.in/careers
"""

from datetime import datetime
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict
import logging
import re

logger = logging.getLogger(__name__)


class AISATSScraper(BaseScraper):
    """Scraper for AISATS (Air India SATS) Careers"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, "aisats", db_manager=db_manager)
        self.site_config = config.get("sites", {}).get("aisats", {})
        self.base_url = self.site_config.get("base_url", "https://www.aisats.in")
        self.jobs_url = self.site_config.get(
            "jobs_url", "https://www.aisats.in/careers"
        )

    async def run(self):
        """Main execution method"""
        self.print_header()

        logger.info(f"Fetching jobs from {self.company_name}...")
        logger.info(f"URL: {self.jobs_url}")

        jobs_raw = await self.fetch_jobs_from_listing()
        jobs = [get_job_dict(**job) for job in jobs_raw]

        if not jobs:
            logger.warning("No jobs found")
            return []

        logger.info(f"Extracted {len(jobs)} jobs")

        # Apply title filtering
        if self.use_filter and self.filter_manager:
            logger.info("Applying title filter...")
            matched_jobs, rejected_jobs, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

            if not matched_jobs:
                logger.info("No jobs matched the filter criteria")
                return []

            jobs = matched_jobs

        # Filter duplicates
        jobs, duplicate_count = await self.filter_new_jobs(jobs)
        if duplicate_count > 0:
            logger.info(f"Filtered out {duplicate_count} duplicate jobs")

        # Save results
        await self.save_results(jobs)
        if jobs:
            self.print_sample(jobs)

        return jobs

    async def fetch_jobs_from_listing(self):
        """Fetch and parse jobs from the AISATS careers page"""
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                logger.info("Loading AISATS careers page...")
                await page.goto(
                    self.jobs_url, wait_until="domcontentloaded", timeout=30000
                )
                await self.random_delay(2, 4)
                await self.simulate_human_behavior(page)

                # AISATS listing structure is often a bit loose.
                # Every job has an "Apply" link. We'll use that as our anchor.
                apply_links = await page.query_selector_all('a[href*="careers-apply"]')

                logger.info(f"Found {len(apply_links)} job apply links")

                for i, link in enumerate(apply_links):
                    try:
                        href = await link.get_attribute("href")
                        if not href:
                            continue

                        job_id_match = re.search(r"careers-apply/(\d+)", href)
                        job_id = (
                            job_id_match.group(1) if job_id_match else f"aisats_ext_{i}"
                        )
                        full_url = (
                            f"{self.base_url}{href}" if href.startswith("/") else href
                        )

                        # Find the container/context for this job
                        # Try to find a reasonably large container that includes both title and link
                        parent = await link.evaluate_handle("""el => {
                            let curr = el.parentElement;
                            for (let i = 0; i < 5; i++) {
                                if (curr.querySelector('h5')) return curr;
                                if (!curr.parentElement) break;
                                curr = curr.parentElement;
                            }
                            return el.parentElement;
                        }""")

                        # Extract title and description from the parent area
                        all_h5 = await parent.query_selector_all("h5")
                        title = ""

                        for h5 in all_h5:
                            text = (await h5.inner_text()).strip()
                            if not text:
                                continue
                            if text.isdigit() or re.match(r"^[\d\s]+$", text):
                                pass
                            elif not title:
                                title = text

                        # If still no title, try looking at the element IMMEDIATELY before the parent/link
                        if not title:
                            # Search for the nearest preceding H5 in the entire DOM if needed
                            title_val = await page.evaluate(rf"""() => {{
                                const link = document.querySelector('a[href*="careers-apply/{job_id}"]');
                                if (!link) return "";
                                let curr = link;
                                while (curr) {{
                                    // Search at same level or parent level
                                    let prev = curr.previousElementSibling;
                                    while (prev) {{
                                        let found = prev.querySelector('h5') || (prev.tagName === 'H5' ? prev : null);
                                        if (found) {{
                                            let t = found.innerText.trim();
                                            if (t && !/^\d+$/.test(t)) return t;
                                        }}
                                        prev = prev.previousElementSibling;
                                    }}
                                    curr = curr.parentElement;
                                    if (curr && curr.tagName === 'BODY') break;
                                }}
                                return "";
                            }}""")
                            if title_val:
                                title = title_val.strip()

                        if not title:
                            title = f"AISATS Job {job_id}"

                        description = ""
                        h6_elem = await parent.query_selector("h6")
                        if h6_elem:
                            description = (await h6_elem.inner_text()).strip()
                        else:
                            # Fallback: get parent text and clean it
                            description = (await parent.inner_text()).strip()
                            # Remove the title and apply text from description
                            description = (
                                description.replace(title, "")
                                .replace("Apply", "")
                                .strip()
                            )

                        # Location extraction
                        location = "India"
                        for loc_code, loc_name in [
                            ("TRV", "Trivandrum"),
                            ("BLR", "Bengaluru"),
                            ("DEL", "Delhi"),
                            ("HYD", "Hyderabad"),
                            ("MAA", "Chennai"),
                            ("BOM", "Mumbai"),
                        ]:
                            if loc_code in title or loc_code in description:
                                location = loc_name
                                break

                        # Date extraction
                        posted_date = ""
                        date_match = re.search(
                            r"(?:Start Date|Posted)[:\s]*([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})",
                            description,
                        )
                        if date_match:
                            posted_date = self.parse_posted_date(date_match.group(1))

                        job_data = {
                            "job_id": f"aisats_{job_id}",
                            "title": title,
                            "company": "AISATS",
                            "source": "aisats",
                            "url": full_url,
                            "apply_url": full_url,
                            "location": location,
                            "posted_date": posted_date
                            or datetime.now().strftime("%Y-%m-%d"),
                            "description": description,
                            "timestamp": datetime.now().isoformat(),
                        }

                        if not any(j["job_id"] == job_data["job_id"] for j in jobs):
                            jobs.append(job_data)

                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break
                    except Exception as e:
                        logger.error(f"  Error parsing job link {i}: {e}")

            except Exception as e:
                logger.error(f"Error scraping AISATS: {e}")
            finally:
                await context.close()
                await browser.close()

        return jobs
