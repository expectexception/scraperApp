import logging
import re
from datetime import datetime
from typing import Optional
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class RiyadhAirScraper(BaseScraper):
    """
    Scraper for Riyadh Air.
    Uses Playwright to navigate their iCIMS job board embedded in an iframe.
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="riyadh_air", db_manager=db_manager)
        self.base_url = "https://globalcareerhub-riyadhair.icims.com"
        # The specific search URL provided by the user
        self.search_url = "https://globalcareerhub-riyadhair.icims.com/jobs/search?hashed=-625885971&mobile=false&width=1492&height=500&bga=true&needsRedirect=false&jan1offset=330&jun1offset=330"
        self.company_name = "Riyadh Air"

    async def fetch_jobs(self) -> list:
        logger.info(
            f"[{self.site_key}] Navigating to {self.search_url} (Headless={self.headless})..."
        )
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                # Direct navigation to search results
                # Using domcontentloaded as icims can be slow with networkidle
                await page.goto(
                    self.search_url, wait_until="domcontentloaded", timeout=90000
                )
                await self.simulate_human_behavior(page)
                await self.random_delay(5, 8)  # Extra time for SPA and iframe to load

                # Riyadh Air uses an iCIMS iframe
                iframe_selector = "iframe#icims_content_iframe"
                try:
                    await page.wait_for_selector(iframe_selector, timeout=30000)
                    logger.info(f"[{self.site_key}] Found iCIMS iframe")
                    iframe = page.frame_locator(iframe_selector)
                except Exception:
                    logger.warning(
                        f"[{self.site_key}] iCIMS iframe not found, attempting to scrape main page"
                    )
                    iframe = page

                # Wait for job rows within the iframe
                try:
                    await iframe.locator(".iCIMS_JobsTable .row").first.wait_for(
                        timeout=20000
                    )
                    logger.info(f"[{self.site_key}] Found job rows in iframe")
                except Exception:
                    logger.warning(
                        f"[{self.site_key}] Timeout waiting for job rows in iframe."
                    )

                # Basic pagination loop (if needed)
                has_next = True
                page_num = 1

                while has_next and page_num <= 5:  # Limit to 5 pages
                    # Extract job listings from current view
                    job_elements = await iframe.locator(".iCIMS_JobsTable .row").all()
                    logger.info(
                        f"[{self.site_key}] Found {len(job_elements)} job rows on page {page_num}"
                    )

                    batch_jobs = []
                    for element in job_elements:
                        title_anchor = element.locator("a.iCIMS_Anchor")
                        title_elem = title_anchor.locator("h3")

                        if await title_anchor.count() > 0:
                            title = (await title_elem.inner_text()).strip()
                            href = await title_anchor.get_attribute("href")

                            # Location is usually in the second span of .header.left
                            loc_elem = element.locator(
                                ".header.left span:nth-of-type(2)"
                            )
                            location = (
                                (await loc_elem.inner_text()).strip()
                                if await loc_elem.count() > 0
                                else "Riyadh"
                            )

                            batch_jobs.append(
                                {"title": title, "url": href, "location": location}
                            )

                    # PRE-FILTER: Skip irrelevant roles before deep fetching
                    matched_batch, _, _ = self.apply_title_filter(batch_jobs)
                    logger.info(
                        f"[{self.site_key}] {len(matched_batch)}/{len(batch_jobs)} jobs passed pre-filter on page {page_num}"
                    )

                    for j_initial in matched_batch:
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break

                        url = j_initial["url"]
                        title = j_initial["title"]
                        location = j_initial["location"]

                        try:
                            if not self.should_process_job(title):
                                continue

                            if await self.is_url_already_scraped(url):
                                continue

                            logger.info(
                                f"[{self.site_key}] Fetching details for: {url}"
                            )
                            detail_page = await context.new_page()
                            await detail_page.goto(
                                url, wait_until="domcontentloaded", timeout=30000
                            )
                            await self.random_delay(1, 2)

                            # iCIMS detail page often has nested iframes or direct content
                            # We'll try to find the description wrap
                            desc_elem = await detail_page.query_selector(
                                ".iCIMS_JobListing, .iCIMS_InfoMsg_Job"
                            )
                            if desc_elem:
                                description = await desc_elem.inner_text()
                            else:
                                description = await self.extract_description_from_page(
                                    detail_page
                                )
                                
                            detail_location = await self.extract_location_from_detail_page(detail_page)
                            if detail_location:
                                location = detail_location
                            
                            job_id = f"riyadhair_{re.sub(r'[^a-zA-Z0-9]', '', url)[-10:]}"

                            job = get_job_dict(
                                job_id=job_id,
                                title=title,
                                company=self.company_name,
                                location=location,
                                url=url,
                                source_url=self.search_url,
                                description=description,
                                source=self.site_key,
                            )
                            jobs.append(job)
                            await detail_page.close()
                        except Exception as e:
                            logger.warning(
                                f"[{self.site_key}] Error detail page {url}: {e}"
                            )

                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    # Check for next page
                    next_btn = iframe.locator('a.iCIMS_PagingArrow[title="Next page"]')
                    if await next_btn.count() > 0 and await next_btn.is_visible():
                        logger.info(f"[{self.site_key}] Navigating to next page...")
                        await next_btn.click()
                        await self.random_delay(3, 5)
                        page_num += 1
                    else:
                        has_next = False

            except Exception as e:
                logger.error(f"[{self.site_key}] Main page error: {e}")
            finally:
                await context.close()
                await browser.close()

        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()

        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs

    async def extract_location_from_detail_page(self, page) -> Optional[str]:
        """Try to extract precise location from the detail page"""
        try:
            # iCIMS detail pages often load job content in an iframe
            iframe_selector = "iframe#icims_content_iframe"
            target_frame = page
            
            try:
                # Quickly check if iframe exists
                iframe_el = await page.query_selector(iframe_selector)
                if iframe_el:
                    target_frame = await iframe_el.content_frame()
                    if not target_frame:
                        target_frame = page
            except Exception:
                pass
                
            # 1. Try standard iCIMS Job Header Data (e.g. Job Locations)
            # Find the header element that contains "Location" and get its value
            header_items = await target_frame.query_selector_all('.iCIMS_JobHeaderGroup dl')
            if not header_items:
                # sometimes they are not in dl tags but divs
                header_items = await target_frame.query_selector_all('.iCIMS_JobHeaderGroup .row')
                
            for item in header_items:
                text = await item.inner_text()
                if text and 'Location' in text:
                    # Usually formatted as "Job Locations \n SA-Riyadh" or similar
                    parts = text.split('\n')
                    if len(parts) >= 2:
                        val = parts[-1].strip()
                        if val and len(val) > 2:
                            return val

            # 2. Try og:description meta tag in the main document
            meta_desc = await page.query_selector('meta[property="og:description"]')
            if meta_desc:
                content = await meta_desc.get_attribute('content')
                if content:
                    # sometimes contains "Job Locations: SA-Riyadh"
                    match = re.search(r'Locations?\s*:?\s*([^|\n]+)', content, re.IGNORECASE)
                    if match:
                        val = match.group(1).strip()
                        if val and len(val) > 2:
                            return val

            # 3. Try searching the body text as a fallback
            body_text = await target_frame.inner_text('body')
            match = re.search(r'Job Locations?\s+([^\n]+)', body_text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                if val and len(val) > 2:
                    return val

        except Exception as e:
            logger.error(f"[{self.site_key}] Error extracting location from detail page: {e}")
            
        return None
