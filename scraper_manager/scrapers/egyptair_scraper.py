"""
Egyptair careers scraper.

Strategy (3-tier):
  1. curl_cffi with Chrome TLS fingerprint (fastest, often bypasses CF turnstile)
  2. Playwright headless with stealth init scripts
  3. Playwright headful (headless=False) as last resort — requires display

If all fail we return [] and log a warning so the run continues.
"""

import asyncio
import logging
import re
from urllib.parse import urljoin

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

CAREERS_URL = "https://www.egyptair.com/en/about-egyptair/Pages/careers.aspx"
CF_PHRASES = (
    "just a moment",
    "please wait",
    "checking your browser",
    "performing security",
)


def _is_cf(title: str) -> bool:
    return any(p in title.lower() for p in CF_PHRASES)


class EgyptairScraper(BaseScraper):
    """
    Egyptair scraper with 3-tier Cloudflare bypass strategy.
    Tier-1: curl_cffi (TLS fingerprint spoofing)
    Tier-2: Playwright headless + stealth
    Tier-3: Playwright headful (needs display)
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="egyptair", db_manager=db_manager)
        self.base_url = CAREERS_URL
        self.company_name = "Egyptair"

    # ------------------------------------------------------------------ #
    #  Tier 1: curl_cffi                                                   #
    # ------------------------------------------------------------------ #
    async def _fetch_with_curl_cffi(self) -> list:
        """Use curl_cffi with Chrome110 TLS impersonation."""
        try:
            from curl_cffi import requests as curl_req

            logger.info(f"[{self.site_key}] Tier-1: curl_cffi attempt...")
            resp = curl_req.get(
                CAREERS_URL,
                impersonate="chrome110",
                timeout=30,
                headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://www.google.com/",
                },
            )
            if resp.status_code == 200 and not _is_cf(resp.text[:500].lower()):
                return self._parse_html(resp.text)
            logger.warning(
                f"[{self.site_key}] Tier-1 blocked (status={resp.status_code})"
            )
        except Exception as e:
            logger.warning(f"[{self.site_key}] Tier-1 error: {e}")
        return []

    # ------------------------------------------------------------------ #
    #  Tier 2 & 3: Playwright                                              #
    # ------------------------------------------------------------------ #
    async def _fetch_with_playwright(self, headless: bool) -> list:
        from playwright.async_api import async_playwright

        mode = "headless" if headless else "headful"
        logger.info(
            f"[{self.site_key}] Tier-{'2' if headless else '3'}: Playwright {mode}..."
        )
        jobs = []
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless)
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 800},
                    locale="en-US",
                    timezone_id="Africa/Cairo",
                    ignore_https_errors=True,
                )
                # Stealth init script
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    window.chrome = { runtime: {}, loadTimes: ()=>{}, csi: ()=>{}, app: {} };
                    Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
                    Object.defineProperty(navigator, 'languages', { get: () => ['en-US','en'] });
                """)

                page = await context.new_page()
                await page.goto(
                    CAREERS_URL, wait_until="domcontentloaded", timeout=60000
                )

                # Wait up to 30s for CF challenge to clear
                for _ in range(30):
                    title = await page.title()
                    if not _is_cf(title):
                        break
                    await page.wait_for_timeout(1000)
                else:
                    logger.warning(
                        f"[{self.site_key}] CF challenge timed out in {mode} mode"
                    )
                    await browser.close()
                    return []

                await page.wait_for_load_state("networkidle", timeout=10000)
                html = await page.content()
                jobs = self._parse_html(html)
                await browser.close()
        except Exception as e:
            logger.warning(f"[{self.site_key}] Playwright {mode} error: {e}")
        return jobs

    # ------------------------------------------------------------------ #
    #  HTML parser                                                         #
    # ------------------------------------------------------------------ #
    def _parse_html(self, html: str) -> list:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        seen = set()

        # Try structured job containers first
        for container in soup.select(".job-item, .vacancy, .career-item, article.job"):
            link = container.find("a")
            if not link:
                continue
            title = link.text.strip()
            href = urljoin("https://www.egyptair.com", link.get("href", ""))
            if href in seen or not title:
                continue
            seen.add(href)
            loc = container.select_one(".location")
            jobs.append(
                self._make_job(title, href, loc.text.strip() if loc else "Cairo, Egypt")
            )

        # Fallback: scan all links for job/vacancy patterns
        if not jobs:
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                if not any(
                    kw in href.lower() for kw in ("job", "vacanc", "career", "recruit")
                ):
                    continue
                full_url = urljoin("https://www.egyptair.com", href)
                title = a.text.strip()
                if not title or len(title) < 5 or full_url in seen:
                    continue
                seen.add(full_url)
                jobs.append(self._make_job(title, full_url, "Cairo, Egypt"))

        logger.info(f"[{self.site_key}] Parsed {len(jobs)} job links from HTML")
        return jobs

    def _make_job(self, title: str, url: str, location: str) -> dict:
        job_id = f"egyptair_{re.sub(r'[^a-zA-Z0-9]', '', url)[-12:]}"
        return get_job_dict(
            job_id=job_id,
            title=title,
            company=self.company_name,
            location=location,
            url=url,
            source_url=CAREERS_URL,
            description="",
            source=self.site_key,
        )

    # ------------------------------------------------------------------ #
    #  Main fetch with fallback chain                                      #
    # ------------------------------------------------------------------ #
    async def fetch_jobs(self) -> list:
        logger.info(
            f"[{self.site_key}] Starting Egyptair fetch with CF bypass chain..."
        )

        # Tier 1 — curl_cffi (no browser needed)
        jobs = await self._fetch_with_curl_cffi()
        if jobs:
            logger.info(f"[{self.site_key}] Tier-1 succeeded: {len(jobs)} jobs")
            return jobs

        # Tier 2 — Playwright headless + stealth
        jobs = await self._fetch_with_playwright(headless=True)
        if jobs:
            logger.info(f"[{self.site_key}] Tier-2 succeeded: {len(jobs)} jobs")
            return jobs

        # Tier 3 — Playwright headful (needs display; skip if DISPLAY not set)
        import os

        if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            jobs = await self._fetch_with_playwright(headless=False)
            if jobs:
                logger.info(f"[{self.site_key}] Tier-3 succeeded: {len(jobs)} jobs")
                return jobs
        else:
            logger.warning(
                f"[{self.site_key}] No display available — skipping Tier-3 headful mode"
            )

        logger.warning(
            f"[{self.site_key}] All CF bypass tiers failed — returning empty"
        )
        return []

    async def fetch_job_descriptions(self, jobs) -> list:
        """Fetch full description from each job detail page using curl_cffi."""
        from curl_cffi import requests as curl_req

        for job in jobs:
            try:
                resp = curl_req.get(
                    job["url"],
                    impersonate="chrome110",
                    timeout=20,
                )
                if resp.status_code == 200:
                    from bs4 import BeautifulSoup

                    soup = BeautifulSoup(resp.text, "html.parser")
                    content = (
                        soup.find("div", class_="job-description")
                        or soup.find("div", id="mainContent")
                        or soup.find("main")
                        or soup.find("article")
                    )
                    if content:
                        job["description"] = content.get_text(" ", strip=True)[:3000]
            except Exception as e:
                logger.warning(
                    f"[{self.site_key}] Desc error for {job.get('url')}: {e}"
                )
            await asyncio.sleep(1)
        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        if not jobs:
            return []

        if self.use_filter and self.filter_manager:
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)
            if not jobs:
                return []

        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []

        jobs = await self.fetch_job_descriptions(jobs)
        await self.save_results(jobs)
        return jobs
