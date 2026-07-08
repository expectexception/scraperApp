import asyncio
import logging
import re
import email.utils
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import urljoin, quote

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

KEYWORDS = ["dispatcher", "operations", "flight operations", "OCC", "crew scheduling"]


class AmericanAirlinesScraper(BaseScraper):
    """
    Scraper for American Airlines Careers (using RSS feeds to bypass WAF/Akamai blocks)
    """

    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="american_airlines", db_manager=db_manager)
        self.company_name = "American Airlines"
        self.base_url = "https://jobs.aa.com"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        seen_urls = set()
        logger.info(f"[{self.site_key}] Fetching American Airlines career RSS feeds...")

        for keyword in KEYWORDS:
            if self.max_jobs and len(jobs) >= self.max_jobs:
                break

            # SuccessFactors RSS feed with keyword
            rss_url = f"https://jobs.aa.com/services/rss/job/?locale=en_US&keywords=({quote(keyword)})"
            logger.info(f"[{self.site_key}] Querying RSS feed for '{keyword}'...")

            try:
                response = await self.make_request(rss_url)
                if not response or response.status_code != 200:
                    logger.warning(
                        f"[{self.site_key}] Failed to load RSS feed for '{keyword}'"
                    )
                    continue

                soup = BeautifulSoup(response.text, "xml")
                items = soup.find_all("item")
                logger.info(
                    f"[{self.site_key}] Found {len(items)} RSS items for '{keyword}'"
                )

                for item in items:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    url_elem = item.find("link")
                    url = url_elem.text.strip() if url_elem else ""
                    if not url or url in seen_urls:
                        continue

                    # Parse Title and Location
                    title_elem = item.find("title")
                    raw_title = title_elem.text.strip() if title_elem else "Unknown Title"

                    # Location is typically inside parentheses at the end of the title
                    location = "Fort Worth, TX"  # Default fallback
                    title = raw_title
                    loc_match = re.search(r"\(([^)]+)\)$", raw_title)
                    if loc_match:
                        location = loc_match.group(1).strip()
                        # Clean up title by removing the location suffix
                        title = re.sub(r"\s*\([^)]+\)$", "", raw_title).strip()

                    # Parse Description HTML
                    desc_elem = item.find("description")
                    description = ""
                    if desc_elem:
                        desc_soup = BeautifulSoup(desc_elem.text, "html.parser")
                        description = desc_soup.get_text(" ", strip=True)

                    # Parse Posted Date
                    pub_date_elem = item.find("pubDate")
                    posted_date = None
                    if pub_date_elem:
                        try:
                            dt = email.utils.parsedate_to_datetime(
                                pub_date_elem.text.strip()
                            )
                            posted_date = dt.date().isoformat()
                        except Exception:
                            pass

                    if not posted_date:
                        posted_date = datetime.now().date().isoformat()

                    seen_urls.add(url)
                    jobs.append(
                        {
                            "company": self.company_name,
                            "title": title,
                            "location": location,
                            "url": url,
                            "source": self.site_key,
                            "apply_url": url,
                            "description": description,
                            "posted_date": posted_date,
                        }
                    )
            except Exception as e:
                logger.error(
                    f"[{self.site_key}] Error fetching feed for '{keyword}': {e}"
                )

            # Polite delay between keywords
            await asyncio.sleep(1)

        logger.info(f"[{self.site_key}] Found a total of {len(jobs)} unique jobs")
        return jobs

    async def run(self):
        """Main entry point for the scraper"""
        self.print_header()
        jobs_raw = await self.fetch_jobs()
        jobs = [get_job_dict(**job) for job in jobs_raw]
        if not jobs:
            return []

        if self.use_filter and self.filter_manager:
            logger.info(f"[{self.site_key}] Applying filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
