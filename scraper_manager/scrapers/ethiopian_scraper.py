import logging
from playwright.async_api import async_playwright
import re

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class EthiopianScraper(BaseScraper):
    """
    Scraper for Ethiopian Airlines
    URL: https://corporate.ethiopianairlines.com/AboutEthiopian/careers/vacancies
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="ethiopian", db_manager=db_manager)
        self.base_url = (
            "https://corporate.ethiopianairlines.com/AboutEthiopian/careers/vacancies"
        )
        self.company_name = "Ethiopian Airlines"

    async def fetch_jobs(self) -> list:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")

                try:
                    await page.goto(
                        self.base_url, wait_until="networkidle", timeout=60000
                    )
                except Exception as e:
                    logger.error(f"[{self.site_key}] Navigation failed: {e}")
                    return []

                # Check for table or list of jobs
                links = await page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('a'))
                        .map(a => ({t: a.innerText.trim(), h: a.href}))
                        .filter(a => a.t && a.t.length > 5 && (a.h.includes('vacancy') || a.h.includes('job') || a.h.includes('career')))
                }""")

                logger.info(f"[{self.site_key}] Found {len(links)} potential job links")

                seen_urls = set()
                job_urls = []
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
                            "vacancies",
                            "career",
                        ]
                        if (
                            any(kw == title.lower() for kw in skip_words)
                            or title.lower() in skip_words
                        ):
                            continue
                        # If the URL is just the main vacancies page itself, skip it
                        if "vacancies" in href.lower() and (
                            "detail" not in href.lower()
                            and "job" not in href.lower()
                            and len(href.split("/")) < 6
                        ):
                            continue
                        seen_urls.add(href)
                        job_urls.append((href, title))

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
                        h1 = detail_page.locator("h1, h2").first
                        if await h1.is_visible():
                            extracted = await h1.inner_text()
                            if len(extracted) > 5:
                                real_title = extracted

                        description = ""
                        detail_page.locator(".job-description, .content, main, article")
                        for loc in [".job-description", ".content", "main", "article"]:
                            elem = detail_page.locator(loc).first
                            if await elem.is_visible():
                                description = await elem.inner_html()
                                break

                        if not description:
                            description = await self.extract_description_from_page(
                                detail_page
                            )

                        location = "Ethiopia"
                        posted_date = await self.extract_posted_date_from_page(
                            detail_page
                        )

                        job_id = f"ethiopian_{i + 1}"
                        match = re.search(r"([0-9a-zA-Z\-]+)$", url)
                        if match:
                            job_id = f"ethiopian_{match.group(1)}"

                        job = get_job_dict(
                            job_id=job_id,
                            title=real_title,
                            company=self.company_name,
                            location=location,
                            url=url,
                            source_url=url,
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
