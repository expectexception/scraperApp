import asyncio
import logging
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

SEARCH_URL = "https://careers.qantas.com/jobs/jobs-in-operations-safety/?per_page=30"
BASE_URL = "https://careers.qantas.com"


class QantasScraper(BaseScraper):
    """
    Scraper for Qantas Group Careers (Applyflow SPA + HTTP/2)
    URL: https://careers.qantas.com/jobs/jobs-in-operations-safety/?per_page=30
    Uses Playwright Firefox because:
      - Chromium gets net::ERR_HTTP2_PROTOCOL_ERROR on Qantas's server
      - Firefox handles the HTTP/2 negotiation perfectly
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="qantas", db_manager=db_manager)
        self.base_url = SEARCH_URL
        self.company_name = "Qantas"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Launching Playwright Firefox to scrape Qantas jobs...")

        async with async_playwright() as p:
            browser = await p.firefox.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                ] if not self.headless else []
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
                viewport={"width": 1280, "height": 800},
            )
            page = await context.new_page()

            try:
                logger.info(f"[{self.site_key}] Navigating to {SEARCH_URL}...")
                await page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=45000)

                # Wait for Applyflow SPA to render job cards
                try:
                    await page.wait_for_selector(
                        ".afp-card, [class*='job-card'], [class*='afp-job'], a[href*='/jobs/job-details/']",
                        timeout=25000,
                    )
                    logger.info(f"[{self.site_key}] Job cards loaded")
                except Exception:
                    logger.warning(f"[{self.site_key}] Job card selector timed out, trying to scrape anyway")

                await asyncio.sleep(3)

                # Try to click the accept-all cookies button if present
                try:
                    accept_btn = await page.query_selector("button:has-text('Accept'), #onetrust-accept-btn-handler, [aria-label*='accept']")
                    if accept_btn:
                        await accept_btn.click()
                        await asyncio.sleep(1)
                except Exception:
                    pass

                # Extract job cards from the rendered DOM
                cards = await page.query_selector_all(
                    ".afp-card, .afp-job-card, [class*='job-card'], [class*='afp-job']"
                )

                if not cards:
                    logger.info(f"[{self.site_key}] Falling back to link scraping")
                    cards = await page.query_selector_all("a[href*='job-details'], a.afp-btn-view-job")

                logger.info(f"[{self.site_key}] Found {len(cards)} job cards/links")

                for card in cards:
                    try:
                        title_el = await card.query_selector("h2, h3, .job-title, [class*='title']")
                        title = await title_el.inner_text() if title_el else await card.inner_text()
                        title = title.strip()[:200]

                        href = await card.get_attribute("href") or ""
                        if not href:
                            link_el = await card.query_selector("a[href]")
                            href = await link_el.get_attribute("href") if link_el else ""

                        if not href:
                            continue

                        job_url = href if href.startswith("http") else f"{BASE_URL}{href}"

                        loc_el = await card.query_selector("[class*='location'], [class*='Location']")
                        location = (await loc_el.inner_text()).strip() if loc_el else "Australia"

                        if title and len(title) > 3:
                            jobs.append(
                                {
                                    "company": self.company_name,
                                    "title": title,
                                    "location": location,
                                    "url": job_url,
                                    "source_url": job_url,
                                    "apply_url": job_url,
                                    "is_active": True,
                                    "description": "",
                                }
                            )

                    except Exception as e:
                        logger.warning(f"[{self.site_key}] Error parsing job card: {e}")

            except Exception as e:
                logger.error(f"[{self.site_key}] Playwright failed: {e}")
            finally:
                await context.close()
                await browser.close()

        # Deduplicate by URL
        seen = set()
        unique_jobs = []
        for j in jobs:
            if j["url"] not in seen:
                seen.add(j["url"])
                unique_jobs.append(j)

        logger.info(f"[{self.site_key}] Found {len(unique_jobs)} unique jobs")
        return unique_jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        if not jobs:
            return []

        logger.info(
            f"[{self.site_key}] Fetching descriptions for {len(jobs)} jobs via Playwright Firefox..."
        )

        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
                viewport={"width": 1280, "height": 800},
            )
            page = await context.new_page()

            enriched = []
            for job in jobs:
                try:
                    try:
                        await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_selector(".afp-job-description", timeout=10000)
                    except Exception as e:
                        logger.warning(f"[{self.site_key}] Timeout waiting for description selector: {e}")

                    desc_el = await page.query_selector(
                        ".afp-job-description, .afp-job-content, .job-content"
                    )
                    if desc_el:
                        job["description"] = (await desc_el.inner_text()).strip()[:5000]

                except Exception as e:
                    logger.warning(
                        f"[{self.site_key}] Failed detail for {job['title']}: {e}"
                    )

                job_dict = get_job_dict(
                    job_id=f"{self.site_key}_{hash(job['url'])}",
                    title=job["title"],
                    company=job["company"],
                    location=job["location"],
                    url=job["url"],
                    source_url=self.base_url,
                    description=job.get("description", ""),
                    apply_url=job["url"],
                    source=self.site_key,
                )
                enriched.append(job_dict)
                await asyncio.sleep(0.5)

            await context.close()
            await browser.close()

        return enriched

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        if not jobs:
            return []

        matched_jobs, _, _ = self.apply_title_filter(jobs)
        if not matched_jobs:
            return []

        new_jobs, _ = await self.filter_new_jobs(matched_jobs)
        if not new_jobs:
            return []

        final_jobs = await self.fetch_job_descriptions(new_jobs)
        await self.save_results(final_jobs)
        return final_jobs
