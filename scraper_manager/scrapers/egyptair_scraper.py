import asyncio
import logging
import re
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

_CF_CHALLENGE_TITLE_PHRASES = ("just a moment", "please wait", "checking your browser", "performing security")

def _is_cloudflare_challenge(title: str) -> bool:
    return any(p in title.lower() for p in _CF_CHALLENGE_TITLE_PHRASES)


class EgyptairScraper(BaseScraper):
    """
    Scraper for Egyptair.
    Uses Playwright with headful mode (headless=False) to bypass Cloudflare WAF.
    Cloudflare auto-solves for real browsers; we wait up to 30 s for the challenge
    to clear before proceeding to extract job links.
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='egyptair', db_manager=db_manager)
        self.base_url = "https://www.egyptair.com/en/about-egyptair/Pages/careers.aspx"
        self.company_name = "Egyptair"
        # Force headful mode – Cloudflare cannot be solved headlessly
        self.headless = False

    async def _wait_for_cloudflare(self, page, max_wait_ms: int = 30000) -> bool:
        """
        Poll page title every second until the Cloudflare challenge clears.
        Returns True if we passed the challenge, False if timed out.
        """
        waited = 0
        poll_interval = 1000
        while waited < max_wait_ms:
            title = await page.title()
            if not _is_cloudflare_challenge(title):
                logger.info(f"[{self.site_key}] Cloudflare challenge cleared (title: {title!r})")
                return True
            logger.debug(f"[{self.site_key}] Waiting for CF challenge... ({waited // 1000}s, title={title!r})")
            await page.wait_for_timeout(poll_interval)
            waited += poll_interval
        logger.warning(f"[{self.site_key}] Cloudflare challenge did NOT clear after {max_wait_ms // 1000}s")
        return False

    async def fetch_jobs(self) -> list:
        logger.info(f"[{self.site_key}] Navigating to {self.base_url} (headless={self.headless})...")
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                await page.goto(self.base_url, wait_until='domcontentloaded', timeout=60000)

                # If Cloudflare challenge appears, wait for auto-solve (works in headful mode)
                title = await page.title()
                if _is_cloudflare_challenge(title):
                    logger.info(f"[{self.site_key}] Cloudflare challenge detected – waiting for auto-solve...")
                    passed = await self._wait_for_cloudflare(page, max_wait_ms=30000)
                    if not passed:
                        logger.error(
                            f"[{self.site_key}] Blocked by Cloudflare. "
                            "Run with headless=False on a desktop session to bypass."
                        )
                        return []
                    # Wait a bit more for page content to render after challenge clears
                    await page.wait_for_load_state('networkidle', timeout=15000)

                await self.simulate_human_behavior(page)

                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a'))
                        .map(a => ({t: (a.innerText || '').trim(), h: a.href}))
                        .filter(a => a.h && (
                            a.h.includes('job') || a.h.includes('vacancy') ||
                            a.h.includes('career') || a.h.includes('vacan')
                        ))
                }''')

                logger.info(f"[{self.site_key}] Found {len(links)} potential job links")

                seen_urls = set()
                job_urls = []
                for link in links:
                    href = link['h']
                    title = link['t']
                    if href and href not in seen_urls and self.is_job_link(title, href):
                        seen_urls.add(href)
                        job_urls.append((href, title))

                for url, title in job_urls:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    try:
                        if not self.should_process_job(title):
                            continue
                        if await self.is_url_already_scraped(url):
                            continue

                        logger.info(f"[{self.site_key}] Fetching details for: {url}")
                        detail_page = await context.new_page()
                        await detail_page.goto(url, wait_until='domcontentloaded', timeout=30000)
                        await self.random_delay(1, 2)

                        description = await self.extract_description_from_page(detail_page)
                        job_id = f"{self.site_key}_{re.sub(r'[^a-zA-Z0-9]', '', url)[-10:]}"

                        job = get_job_dict(
                            job_id=job_id,
                            title=title,
                            company=self.company_name,
                            location="Cairo, Egypt",
                            url=url,
                            source_url=self.base_url,
                            description=description,
                            source=self.site_key,
                        )
                        jobs.append(job)
                        await detail_page.close()
                    except Exception as e:
                        logger.warning(f"[{self.site_key}] Error on detail page {url}: {e}")

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

    async def setup_stealth_page(self, browser):
        """Create a stealthy browser context to reduce bot-detection signals."""
        context = await browser.new_context(
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/124.0.0.0 Safari/537.36'
            ),
            viewport={'width': 1280, 'height': 800},
            locale='en-US',
            timezone_id='Africa/Cairo',
            ignore_https_errors=True,
        )

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications'
                    ? Promise.resolve({ state: 'denied' })
                    : originalQuery(parameters)
            );
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        """)

        page = await context.new_page()

        try:
            cdp = await context.new_cdp_session(page)
            await cdp.send("Network.setUserAgentOverride", {
                "userAgent": (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/124.0.0.0 Safari/537.36'
                ),
                "platform": "Win32",
                "acceptLanguage": "en-US,en;q=0.9",
            })
        except Exception as e:
            logger.warning(f"[{self.site_key}] CDP stealth error: {e}")

        return page, context

