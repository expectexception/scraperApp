import logging
import re
import itertools
from urllib.parse import urlsplit, urlunsplit
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class RyanairScraper(BaseScraper):
    """
    Scraper for Ryanair.
    URL: https://careers.ryanair.com/jobs/
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="ryanair", db_manager=db_manager)
        # Strip any leftover narrow "search=" query param from config — it was
        # previously hardcoded to "?search=Dispa", which limited the whole
        # listing to dispatcher-titled postings only and hid everything else.
        configured_url = self.site_config.get("jobs_url") or "https://careers.ryanair.com/jobs/"
        split = urlsplit(configured_url)
        self.base_url = urlunsplit((split.scheme, split.netloc, split.path or "/jobs/", "", ""))
        self.company_name = "Ryanair"

    async def fetch_jobs(self) -> list:
        logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
        jobs = []
        job_urls = []
        seen_urls = set()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                for page_num in itertools.count(1):
                    if self.max_pages and page_num > self.max_pages:
                        break
                    page_url = f"{self.base_url}?page={page_num}"
                    try:
                        await page.goto(
                            page_url, wait_until="networkidle", timeout=60000
                        )
                    except Exception as e:
                        logger.error(f"[{self.site_key}] Navigation failed on page {page_num}: {e}")
                        break

                    if page_num == 1:
                        # Handling cookie consent
                        try:
                            cookie_btn = page.locator("text=Yes, text=Accept All").first
                            if await cookie_btn.is_visible():
                                await cookie_btn.click()
                                await page.wait_for_timeout(1000)
                        except:
                            pass

                    links = await page.evaluate("""() => {
                        return Array.from(document.querySelectorAll('a'))
                            .map(a => ({t: a.innerText.trim(), h: a.href}))
                            .filter(a => a.t && a.t.length > 5 && (a.h.includes('/job/') || a.h.includes('successfactors.eu') || a.h.includes('workable.com') || a.h.includes('/jobs/')))
                    }""")

                    new_count = 0
                    for link in links:
                        href = link["h"]
                        title = link["t"]
                        if href and href not in seen_urls and self.is_job_link(title, href):
                            skip_words = [
                                "home",
                                "news",
                                "faq",
                                "cookie",
                                "login",
                                "impressum",
                                "privacy",
                                "about",
                            ]
                            if (
                                any(kw == title.lower() for kw in skip_words)
                                or title.lower() in skip_words
                            ):
                                continue
                            seen_urls.add(href)
                            job_urls.append((href, title))
                            new_count += 1

                    logger.info(f"[{self.site_key}] Page {page_num}: {new_count} new job links (total {len(job_urls)})")

                    if new_count == 0:
                        break

                for i, (url, title) in enumerate(job_urls):
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    try:
                        if not self.should_process_job(title):
                            continue

                        if await self.is_url_already_scraped(url):
                            continue

                        logger.info(f"[{self.site_key}] Fetching details for: {url}")
                        detail_page = await context.new_page()
                        await detail_page.goto(
                            url, wait_until="domcontentloaded", timeout=30000
                        )
                        await detail_page.wait_for_timeout(2000)

                        real_title = title
                        h1 = detail_page.locator("h1").first
                        if await h1.is_visible():
                            extracted = await h1.inner_text()
                            if len(extracted) > 5:
                                real_title = extracted

                        description = ""
                        for loc in [
                            ".jobdescription",
                            ".job-description",
                            "main",
                            "article",
                        ]:
                            elem = detail_page.locator(loc).first
                            if await elem.is_visible():
                                description = await elem.inner_html()
                                break

                        if not description:
                            description = await self.extract_description_from_page(
                                detail_page
                            )

                        location = "Ireland"
                        for loc in [".jobGeoLocation", ".location"]:
                            elem = detail_page.locator(loc).first
                            if await elem.is_visible():
                                loc_text = await elem.inner_text()
                                if loc_text:
                                    location = loc_text.strip()
                                break

                        posted_date = await self.extract_posted_date_from_page(
                            detail_page
                        )

                        job_id = f"ryanair_{i + 1}"
                        match = re.search(r"job/[^/]+/[^/]+(?:/(\d+))?", url)
                        if match and match.group(1):
                            job_id = f"ryanair_{match.group(1)}"

                        job = get_job_dict(
                            job_id=job_id,
                            title=real_title,
                            company=self.company_name,
                            location=location,
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
