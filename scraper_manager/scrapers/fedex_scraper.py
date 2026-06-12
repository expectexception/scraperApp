import logging
import re
from typing import Optional
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class FedexScraper(BaseScraper):
    """
    Scraper for FedEx
    URL: https://careers.fedex.com/jobs
    """

    def __init__(self, config, db_manager=None, site_key="fedex"):
        super().__init__(config, site_key=site_key, db_manager=db_manager)
        self.site_config = config.get("sites", {}).get(site_key, {})
        self.base_url = self.site_config.get("jobs_url", "https://careers.fedex.com/jobs")
        self.company_name = "FedEx"

    async def fetch_jobs(self) -> list:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(
                    self.base_url, wait_until="domcontentloaded", timeout=60000
                )
                await page.wait_for_timeout(5000)

                # Handle cookie banner
                try:
                    await page.evaluate("""() => {
                        const el = document.getElementById('usercentrics-cmp-ui');
                        if (el) el.remove();
                    }""")
                    cookie_btn = page.locator(
                        '#onetrust-accept-btn-handler, button[data-testid="uc-accept-all-button"]'
                    ).first
                    if await cookie_btn.is_visible():
                        logger.info(f"[{self.site_key}] Accepting cookies...")
                        await cookie_btn.click()
                        await page.wait_for_timeout(2000)
                except Exception as e:
                    logger.debug(f"[{self.site_key}] No cookie banner found: {e}")

                page_count = 1
                while True:
                    if self.max_pages and page_count > self.max_pages:
                        break

                    logger.info(f"[{self.site_key}] Processing page {page_count}...")

                    # Ensure results are loaded
                    try:
                        await page.wait_for_selector(
                            ".results-list__item", timeout=15000
                        )
                    except:
                        logger.warning(
                            f"[{self.site_key}] Timeout waiting for .results-list__item on page {page_count}"
                        )
                        break

                    # Scroll a bit to trigger any lazy loading
                    await page.evaluate("window.scrollBy(0, 500)")
                    await page.wait_for_timeout(2000)

                    # Extract jobs from the list
                    job_items = await page.query_selector_all(".results-list__item")
                    if not job_items:
                        logger.warning(
                            f"[{self.site_key}] No job items found on page {page_count}"
                        )
                        break

                    logger.info(
                        f"[{self.site_key}] Found {len(job_items)} job items on page {page_count}"
                    )

                    page_jobs_data = []
                    for item in job_items:
                        try:
                            # Link and Title
                            link_el = await item.query_selector(
                                "a.results-list__item-title--link"
                            )
                            if not link_el:
                                continue

                            title = await link_el.inner_text()
                            url = await link_el.get_attribute("href")
                            if url and not url.startswith("http"):
                                url = "https://careers.fedex.com" + url

                            # Location
                            location = await item.evaluate("""el => {
                                let locEl = el.querySelector('.results-list__item-location');
                                if (locEl) return locEl.innerText.trim();
                                
                                // Regex fallback within the item text
                                let text = el.innerText;
                                let match = text.match(/Location\\s*:?\\s*([^\\n]+)/i);
                                if (match && match[1].trim().length > 2) {
                                    return match[1].trim();
                                }
                                return "Global";
                            }""")
                            page_jobs_data.append(
                                {
                                    "title": title.strip(),
                                    "url": url,
                                    "location": location.strip(),
                                }
                            )
                        except Exception as e:
                            logger.error(f"[{self.site_key}] Error parsing item: {e}")
                            continue

                    # Visit each job detail page
                    for job_data in page_jobs_data:
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break

                        url = job_data["url"]
                        title = job_data["title"]

                        if not self.is_job_link(title, url):
                            continue

                        if not self.should_process_job(title):
                            continue

                        if await self.is_url_already_scraped(url):
                            continue

                        try:
                            logger.info(
                                f"[{self.site_key}] Fetching details for: {url}"
                            )
                            detail_page = await context.new_page()
                            await detail_page.goto(
                                url, wait_until="domcontentloaded", timeout=30000
                            )
                            await detail_page.wait_for_timeout(2000)

                            description = await self.extract_description_from_page(
                                detail_page
                            )
                            # Specifically look for Phenom People description class
                            phenom_desc = await detail_page.query_selector(
                                ".job-description, .job-details-brief"
                            )
                            if phenom_desc:
                                description = await phenom_desc.inner_text()

                            # Job ID
                            job_id_match = re.search(r"/job/([^/]+)/", url)
                            job_id = (
                                f"fedex_{job_id_match.group(1)}"
                                if job_id_match
                                else f"fedex_{hash(url)}"
                            )

                            # Extract location from detail page as it's more accurate
                            detail_location = (
                                await self.extract_location_from_detail_page(
                                    detail_page
                                )
                            )
                            if detail_location:
                                job_data["location"] = detail_location

                            job = get_job_dict(
                                job_id=job_id,
                                title=title,
                                company=self.company_name,
                                location=job_data["location"],
                                url=url,
                                source_url=self.base_url,
                                description=description,
                                apply_url=url,
                                posted_date=None,  # Usually not in list for Phenom
                                source=self.site_key,
                            )

                            jobs.append(job)
                            await detail_page.close()
                            await self.random_delay(1, 3)

                        except Exception as e:
                            logger.error(
                                f"[{self.site_key}] Error fetching job detail ({url}): {e}"
                            )
                            continue

                    # Pagination
                    try:
                        next_btn = page.locator("a.page-link-next").first
                        if await next_btn.is_visible() and await next_btn.is_enabled():
                            logger.info(f"[{self.site_key}] Clicking Next button...")
                            await next_btn.click()
                            await page.wait_for_timeout(5000)
                            page_count += 1
                        else:
                            logger.info(f"[{self.site_key}] No more pages found.")
                            break
                    except Exception as e:
                        logger.error(
                            f"[{self.site_key}] Error navigating to next page: {e}"
                        )
                        break

            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
            finally:
                await context.close()
                await browser.close()

        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        jobs = [j for j in jobs if j is not None]

        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs

    async def extract_location_from_detail_page(self, page) -> Optional[str]:
        """Try to extract location from the detail page using multiple methods"""
        try:
            # 1. Try JSON-LD (most reliable)
            scripts = await page.query_selector_all(
                'script[type="application/ld+json"]'
            )
            for s in scripts:
                try:
                    txt = await s.inner_text()
                    import json as _json

                    data = _json.loads(txt)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if isinstance(item, dict) and item.get("@type") == "JobPosting":
                            loc = item.get("jobLocation")
                            if isinstance(loc, dict):
                                addr = loc.get("address")
                                if isinstance(addr, dict):
                                    parts = []
                                    if addr.get("addressLocality"):
                                        parts.append(addr.get("addressLocality"))
                                    if addr.get("addressRegion"):
                                        parts.append(addr.get("addressRegion"))
                                    if addr.get("postalCode"):
                                        parts.append(addr.get("postalCode"))
                                    if addr.get("addressCountry"):
                                        parts.append(addr.get("addressCountry"))
                                    if parts:
                                        return ", ".join(parts)
                                elif isinstance(addr, str):
                                    return addr
                except Exception as e:
                    logger.debug(
                        f"[{self.site_key}] Error parsing JSON-LD for location: {e}"
                    )
                    continue

            # 2. Try specific CSS selector
            loc_el = await page.query_selector(
                "li.job-details-brief__list-item--location .job-details-brief__list-item-value"
            )
            if loc_el:
                text = await loc_el.inner_text()
                if text and len(text.strip()) > 2:
                    return text.strip()

            # 3. Fallback: Search for "Location:" in text
            body_text = await page.inner_text("body")
            match = re.search(r"Location\s*:?\s*([^\n]+)", body_text, re.IGNORECASE)
            if match and len(match.group(1).strip()) > 2:
                return match.group(1).strip()

        except Exception as e:
            logger.error(
                f"[{self.site_key}] Error extracting location from detail page: {e}"
            )

        return None

    def is_job_link(self, title, url):
        """Helper to validate if a link is actually a job"""
        if not title or len(title) < 3:
            return False
        if "/job/" not in url:
            return False
        return True

class FedexEuroDispatchScraper(FedexScraper):
    """Scraper for FedEx European Operations Dispatch"""
    def __init__(self, config, db_manager=None):
        super().__init__(config, db_manager=db_manager, site_key="fedex_euro_dispatch")

class AirCanadaScraper(FedexScraper):
    """Scraper for Air Canada (Phenom People)"""
    def __init__(self, config, db_manager=None):
        super().__init__(config, db_manager=db_manager, site_key="air_canada")
