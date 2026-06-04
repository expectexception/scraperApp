import logging
from playwright.async_api import async_playwright
import re

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class EurowingsScraper(BaseScraper):
    """
    Scraper for Eurowings.
    URL: https://apply.lufthansagroup.careers/index.php?ac=search_result&search_criterion_company...
    Lufthansa Group structure.
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="eurowings", db_manager=db_manager)
        # Multiple brand filters for various Eurowings entities
        brands = ["5985", "9061", "9488", "9706", "6004"]
        brand_params = "&".join([f"search_criterion_company%5B%5D={b}" for b in brands])
        self.base_url = f"https://apply.lufthansagroup.careers/index.php?ac=search_result&{brand_params}&language=2"
        self.company_name = "Eurowings"

    async def fetch_jobs(self) -> list:
        logger.info(
            f"[{self.site_key}] Navigating to Lufthansa group careers portal..."
        )
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                try:
                    await page.goto(
                        self.base_url, wait_until="domcontentloaded", timeout=60000
                    )
                    await page.wait_for_timeout(3000)
                except Exception as e:
                    logger.error(f"[{self.site_key}] Navigation failed: {e}")
                    return []

                # Handling cookie consent
                try:
                    cookie_btn = page.locator(
                        'text="Select all", text="Accept all", [data-hook="cc-ccc-btn-confirm-all"], #ensAcceptAll'
                    ).first
                    if await cookie_btn.is_visible():
                        await cookie_btn.click(force=True)
                        await page.wait_for_timeout(2000)
                except:
                    pass

                # Wait for results to load
                try:
                    await page.wait_for_selector("a.jobad-link-wrapper", timeout=30000)
                except:
                    # Try scrolling to trigger load
                    await page.evaluate(
                        "window.scrollTo(0, document.body.scrollHeight)"
                    )
                    await page.wait_for_timeout(3000)
                    try:
                        await page.wait_for_selector(
                            "a.jobad-link-wrapper", timeout=15000
                        )
                    except:
                        logger.warning(
                            f"[{self.site_key}] No job links found after wait/scroll."
                        )

                # Locate all job cards
                job_cards = await page.locator("a.jobad-link-wrapper").all()
                logger.info(
                    f"[{self.site_key}] Found {len(job_cards)} potential job cards"
                )

                initial_jobs = []
                seen_urls = set()

                for card in job_cards:
                    try:
                        href = await card.get_attribute("href")
                        if not href or href in seen_urls:
                            continue

                        # Extract clean title from h2
                        title_el = card.locator("h2")
                        if not await title_el.count():
                            # Fallback to direct text if h2 missing
                            title = await card.inner_text()
                            title = title.split("\n")[0].strip()  # Take first line
                        else:
                            title = await title_el.inner_text()

                        title = title.strip() if title else "Unknown Title"

                        # Extract company and location
                        company_el = card.locator(".company-name")
                        company = (
                            await company_el.inner_text()
                            if await company_el.count()
                            else self.company_name
                        )

                        # Many Lufthansa portal sites have location in .jobad-meta-item > span:nth-child(2)
                        location = "Germany"  # Default
                        loc_el = card.locator(".jobad-meta-item").first
                        if await loc_el.count():
                            loc_spans = await loc_el.locator("span").all()
                            if len(loc_spans) >= 2:
                                location = await loc_spans[1].inner_text()
                            else:
                                location = await loc_el.inner_text()

                        # Basic link cleaning
                        if not href.startswith("http"):
                            href = (
                                f"https://apply.lufthansagroup.careers/{href}"
                                if href.startswith("/")
                                else f"https://apply.lufthansagroup.careers/index.php{href}"
                            )

                        if self.is_job_link(title, href):
                            seen_urls.add(href)
                            initial_jobs.append(
                                {
                                    "title": title,
                                    "url": href,
                                    "company": company.strip(),
                                    "location": location.strip(),
                                }
                            )
                    except Exception as e:
                        logger.debug(f"[{self.site_key}] Skip card due to error: {e}")

                logger.info(
                    f"[{self.site_key}] {len(initial_jobs)} jobs passed link checks. Applying pre-filter..."
                )

                # PRE-FILTER: Filter by title first to skip irrelevant roles COMPLETELY
                matched_initial, _, _ = self.apply_title_filter(initial_jobs)

                logger.info(
                    f"[{self.site_key}] {len(matched_initial)} jobs passed pre-filtering. Fetching details..."
                )

                total_jobs_to_process = len(matched_initial)
                for i, j_initial in enumerate(matched_initial):
                    await self.update_progress(i, total_jobs_to_process)
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    url = j_initial["url"]
                    title = j_initial["title"]

                    try:
                        if await self.is_url_already_scraped(url):
                            continue

                        logger.info(f"[{self.site_key}] Fetching details for: {url}")
                        detail_page = await context.new_page()
                        # Increased timeout for stability
                        try:
                            await detail_page.goto(
                                url, wait_until="domcontentloaded", timeout=45000
                            )
                            await detail_page.wait_for_timeout(2000)
                        except Exception as e:
                            logger.warning(
                                f"[{self.site_key}] Detail page load timeout for {url}: {e}"
                            )
                            await detail_page.close()
                            continue

                        real_title = title
                        h1 = detail_page.locator("h1").first
                        if await h1.is_visible():
                            extracted = await h1.inner_text()
                            if len(extracted) > 5:
                                real_title = extracted.strip()

                        description = ""
                        desc_selectors = [
                            ".jobad-content",
                            ".job-description",
                            'div[id*="jobad"]',
                            "main",
                        ]
                        for selector in desc_selectors:
                            elem = detail_page.locator(selector).first
                            if await elem.is_visible():
                                description = await elem.inner_html()
                                break

                        if not description:
                            description = await self.extract_description_from_page(
                                detail_page
                            )

                        posted_date = await self.extract_posted_date_from_page(
                            detail_page
                        )

                        # Robust Job ID from URL
                        job_id_match = re.search(r"id=(\d+)", url)
                        if not job_id_match:
                            job_id_match = re.search(r"job/(\d+)", url)

                        final_id = (
                            f"eurowings_{job_id_match.group(1)}"
                            if job_id_match
                            else f"eurowings_{hash(url)}"
                        )

                        job = get_job_dict(
                            job_id=final_id,
                            title=real_title,
                            company=j_initial["company"],
                            location=j_initial["location"],
                            url=url,
                            source_url=self.base_url,
                            description=description,
                            apply_url=url,
                            posted_date=posted_date,
                            source=self.site_key,
                        )

                        jobs.append(job)
                        await detail_page.close()

                    except Exception as e:
                        logger.error(
                            f"[{self.site_key}] Error parsing job {i} ({url}): {e}"
                        )
                        continue

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
