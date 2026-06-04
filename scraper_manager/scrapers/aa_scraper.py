#   NOT WORKING BECAUSE OF ANTI SCRAPING MEASURES TECHNOLOGY USED BY THE WEBSITE

#   PENDIAN FOR NOW - @rajatrathee


import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime
from urllib.parse import urljoin
from playwright.async_api import async_playwright

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class AmericanAirlinesScraper(BaseScraper):
    """
    Scraper for American Airlines Careers
    URL: https://jobs.aa.com/search/?q=&locationsearch=
    Platform: React (SuccessFactors/Custom)
    """

    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="aa", db_manager=db_manager)
        self.base_url = "https://jobs.aa.com/search/?q=&locationsearch="
        self.company_name = "American Airlines"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Scrape jobs from American Airlines careers page
        """
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")

                # SuccessFactors RMK sites often block standard Playwright
                # We'll try make_request immediately or as primary fallback
                try:
                    await page.goto(
                        self.base_url, wait_until="domcontentloaded", timeout=30000
                    )
                except Exception as e:
                    logger.warning(f"[{self.site_key}] Main page goto failed: {e}")

                # Check for "Access Denied" or blocking
                title = await page.title()
                logger.info(f"[{self.site_key}] Page Title: {title}")
                if (
                    "Access Denied" in title
                    or "Attention Required" in title
                    or not await page.query_selector('a[href*="/job/"]')
                ):
                    logger.warning(
                        f"[{self.site_key}] Browser blocked or results not found. Trying to use make_request fallback..."
                    )
                    # SuccessFactors RMK pages often list jobs in a table or list
                    # Search URL with query params often works better
                    search_url = f"{self.base_url}/search/?q=&locationsearch="
                    response = await self.make_request(search_url)

                    if response:
                        logger.info(
                            f"[{self.site_key}] Fallback request status: {response.status_code}"
                        )
                        if response.status_code == 200:
                            # Save HTML for debugging
                            with open("aa_fallback.html", "w", encoding="utf-8") as f:
                                f.write(response.text)
                            logger.info(
                                f"[{self.site_key}] Saved fallback HTML to aa_fallback.html"
                            )

                            soup = BeautifulSoup(response.text, "html.parser")
                            # CarrierSite (SuccessFactors RMK) structure
                            # Look for links in the results table
                            links = soup.select(
                                'table[id*="job-table"] a[href*="/job/"], .job-title a[href*="/job/"], a[href*="/job/"]'
                            )
                            if links:
                                logger.info(
                                    f"[{self.site_key}] Found {len(links)} job links via make_request fallback"
                                )
                                seen_urls = set()
                                for link in links:
                                    if len(jobs) >= self.max_jobs:
                                        break
                                    href = link.get("href")
                                    title_text = link.get_text().strip()

                                    if href and title_text and "/job/" in href:
                                        full_url = urljoin(self.base_url, href)
                                        if full_url not in seen_urls:
                                            seen_urls.add(full_url)
                                            # Try to find location in the parent structure (sibling cells)
                                            location = "Unknown"
                                            parent_row = link.find_parent("tr")
                                            if parent_row:
                                                loc_cell = parent_row.select_one(
                                                    ".jobLocation, .location"
                                                )
                                                if loc_cell:
                                                    location = (
                                                        loc_cell.get_text().strip()
                                                    )

                                            jobs.append(
                                                {
                                                    "title": title_text,
                                                    "url": full_url,
                                                    "location": location,
                                                }
                                            )

                                if jobs:
                                    logger.info(
                                        f"[{self.site_key}] Successfully extracted {len(jobs)} jobs via fallback"
                                    )
                                    return jobs
                            else:
                                logger.warning(
                                    f"[{self.site_key}] Fallback returned 200 but no jobs found in HTML."
                                )
                        else:
                            logger.error(
                                f"[{self.site_key}] Fallback request failed with status: {response.status_code}"
                            )
                    else:
                        logger.error(
                            f"[{self.site_key}] Both browser and make_request failed (no response)."
                        )
                    return []

                if not jobs:
                    # Detect job row selector dynamically
                    job_selectors = [
                        "tr.data-row",
                        "tr.job-row",
                        'li[data-testid="jobCard"]',
                        ".job-listing-item",
                        'div[class*="job-card"]',
                    ]

                    target_rows = []
                    for sel in job_selectors:
                        target_rows = await page.query_selector_all(sel)
                        if target_rows:
                            logger.info(
                                f"[{self.site_key}] Found {len(target_rows)} jobs using selector: {sel}"
                            )
                            break

                    if target_rows:
                        # Process target_rows
                        for row in target_rows:
                            if len(jobs) >= self.max_jobs:
                                break
                            try:
                                link_el = await row.query_selector('a[href*="/job/"]')
                                loc_el = await row.query_selector(
                                    '.jobLocation, .location, [class*="location"]'
                                )

                                if link_el:
                                    title_text = await link_el.inner_text()
                                    href = await link_el.get_attribute("href")
                                    location_text = (
                                        await loc_el.inner_text()
                                        if loc_el
                                        else "Unknown"
                                    )

                                    jobs.append(
                                        {
                                            "title": title_text.strip(),
                                            "url": "https://jobs.aa.com" + href
                                            if href.startswith("/")
                                            else href,
                                            "location": location_text.strip().replace(
                                                "\n", " "
                                            ),
                                        }
                                    )
                            except:
                                continue
                    else:
                        # Final fallback: look for any links containing /job/
                        links = await page.query_selector_all(
                            'a[href*="/job/"]:not([href*="facebook"]):not([href*="twitter"])'
                        )
                        if links:
                            logger.info(
                                f"[{self.site_key}] Found {len(links)} job links via fallback"
                            )
                            for link in links:
                                if len(jobs) >= self.max_jobs:
                                    break
                                href = await link.get_attribute("href")
                                title = await link.inner_text()
                                if href and title.strip():
                                    jobs.append(
                                        {
                                            "title": title.strip(),
                                            "url": "https://jobs.aa.com" + href
                                            if href.startswith("/")
                                            else href,
                                            "location": "Unknown",
                                        }
                                    )

                # Detail Extraction
                logger.info(
                    f"[{self.site_key}] Extracting details for {len(jobs)} jobs..."
                )
                for job in jobs:
                    if not job.get("url"):
                        continue

                    if not self.should_process_job(job.get("title")):
                        continue

                    try:
                        if await self.is_url_already_scraped(job["url"]):
                            continue

                        detail_page = await context.new_page()
                        await detail_page.goto(
                            job["url"], wait_until="networkidle", timeout=60000
                        )

                        # Description
                        # Try common selectors for Phenom/SF/React
                        desc_selectors = [
                            'div[data-testid="jobDescription"]',
                            ".jobDescription",
                            ".description",
                            ".job-description",
                            'div[class*="description"]',
                            "#job-details",
                        ]

                        description = ""
                        for sel in desc_selectors:
                            desc_el = await detail_page.query_selector(sel)
                            if desc_el:
                                description = await desc_el.inner_text()
                                if len(description) > 200:
                                    break

                        if not description:
                            description = await self.extract_description_from_page(
                                detail_page
                            )

                        job["description"] = description

                        # Apply Link
                        apply_selectors = [
                            'a[data-testid="applyButton"]',
                            "a.applyButton",
                            'a[class*="apply"]',
                            'button[class*="apply"]',
                        ]

                        for sel in apply_selectors:
                            apply_btn = await detail_page.query_selector(sel)
                            if apply_btn:
                                href = await apply_btn.get_attribute("href")
                                if href:
                                    job["apply_url"] = (
                                        href
                                        if href.startswith("http")
                                        else f"https://jobs.aa.com{href}"
                                    )
                                    break

                        # Set other standard fields
                        job["company"] = self.company_name
                        job["source_url"] = job["url"]
                        job["posted_date"] = datetime.now().isoformat()

                        await detail_page.close()
                        await asyncio.sleep(1)

                    except Exception as e:
                        logger.warning(
                            f"[{self.site_key}] Failed to fetch details for {job.get('title')}: {e}"
                        )
                        try:
                            await detail_page.close()
                        except:
                            pass

            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
            finally:
                await browser.close()

        return jobs

    async def run(self):
        """Main entry point for the scraper"""
        self.print_header()
        jobs = await self.fetch_jobs()
        # Filter out any None values
        jobs = [j for j in jobs if j is not None]

        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
