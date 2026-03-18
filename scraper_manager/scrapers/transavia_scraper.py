import logging
import re
import time
from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

_BASE = "https://werkenbijtransavia.com"
_LIST_URL = f"{_BASE}/l/en/vacatures"


class TransaviaScraper(BaseScraper):
    """
    Scraper for Transavia (werkenbijtransavia.com).
    Uses curl_cffi HTTP requests — no Playwright required.
    The site returns all job listings and details in plain HTML without
    JavaScript rendering or cookie consent blocking.
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='transavia', db_manager=db_manager)
        self.base_url = _LIST_URL
        self.company_name = "Transavia"

    def _get(self, url: str, timeout: int = 20) -> "requests.Response | None":
        try:
            r = curl_requests.get(
                url,
                impersonate='chrome120',
                timeout=timeout,
                headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                },
            )
            if r.status_code != 200:
                logger.warning(f"[{self.site_key}] HTTP {r.status_code} for {url}")
                return None
            return r
        except Exception as e:
            logger.warning(f"[{self.site_key}] Request failed for {url}: {e}")
            return None

    def _extract_jobs_from_listing(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, 'html.parser')
        seen: set[str] = set()
        jobs = []
        for a in soup.find_all('a', href=True):
            href: str = a['href']
            text = a.get_text(strip=True)
            # Only keep canonical English offer pages, skip ?lang= variants and "View job" duplicates
            if '/l/en/o/' not in href or '?' in href or not text or text.lower() == 'view job':
                continue
            full_url = (_BASE + href) if href.startswith('/') else href
            if full_url in seen:
                continue
            seen.add(full_url)
            jobs.append({'title': text, 'url': full_url})
        return jobs

    def _extract_detail(self, url: str, html: str) -> dict:
        soup = BeautifulSoup(html, 'html.parser')

        # Title
        h1 = soup.find('h1')
        title = h1.get_text(strip=True) if h1 else url.rstrip('/').split('/')[-1].replace('-', ' ').title()

        # Location – the page renders: City, Region, Country inline near the title
        location = "Netherlands"
        main = soup.find('main') or soup.body
        if main:
            text = main.get_text(' ', strip=True)
            # Pattern: "On-site City , Region , Country" or plain "City, Country"
            m = re.search(r'(?:On[-\s]?site\s+)?([A-Z][^,]+),\s*([A-Z][^,]+),\s*([A-Z][^\n|$]+)', text)
            if m:
                city, region, country = m.group(1).strip(), m.group(2).strip(), m.group(3).strip().split()[0]
                location = f"{city}, {country}"

        # Description – everything after "Job description" heading
        description = ""
        if main:
            full_text = main.get_text(separator='\n', strip=True)
            marker = re.search(r'Job description\n', full_text, re.IGNORECASE)
            if marker:
                description = full_text[marker.end():].strip()
            else:
                description = full_text

        job_id = f"transavia_{re.sub(r'[^a-zA-Z0-9]', '', url)[-12:]}"
        return get_job_dict(
            job_id=job_id,
            title=title,
            company=self.company_name,
            location=location,
            url=url,
            source_url=self.base_url,
            description=description[:3000],
            source=self.site_key,
        )

    async def fetch_jobs(self) -> list:
        logger.info(f"[{self.site_key}] Fetching job listings from {self.base_url}...")
        jobs = []

        listing_resp = self._get(_LIST_URL)
        if not listing_resp:
            logger.error(f"[{self.site_key}] Failed to fetch job listing page")
            return []

        job_entries = self._extract_jobs_from_listing(listing_resp.text)
        logger.info(f"[{self.site_key}] Found {len(job_entries)} unique job links")

        for entry in job_entries:
            if self.max_jobs and len(jobs) >= self.max_jobs:
                break

            url = entry['url']
            title = entry['title']

            try:
                if not self.should_process_job(title):
                    continue
                if await self.is_url_already_scraped(url):
                    continue

                logger.info(f"[{self.site_key}] Fetching: {title} | {url}")
                detail_resp = self._get(url)
                if not detail_resp:
                    continue

                job = self._extract_detail(url, detail_resp.text)
                # Override title from listing if detail h1 is empty
                if not job.get('title'):
                    job['title'] = title
                jobs.append(job)

                # Small delay to be polite
                time.sleep(1)

            except Exception as e:
                logger.warning(f"[{self.site_key}] Error processing {url}: {e}")

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

