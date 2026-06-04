import logging
from bs4 import BeautifulSoup
from curl_cffi import requests

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class LOTScraper(BaseScraper):
    """
    Scraper for LOT Polish Airlines.
    Requires curl_cffi due to HTTP2 Protocol/complex WAF issues.
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="lot", db_manager=db_manager)
        self.base_url = "https://www.lot.com/pl/pl/kariera"
        self.company_name = "LOT Polish Airlines"

    async def fetch_jobs(self) -> list:
        logger.info(f"[{self.site_key}] Fetching jobs from {self.base_url}")
        jobs = []

        try:
            response = requests.get(self.base_url, impersonate="chrome110", timeout=30)
            if response.status_code != 200:
                logger.error(
                    f"[{self.site_key}] Error accessing site: {response.status_code}"
                )
                return []

            soup = BeautifulSoup(response.content, "html.parser")

            # Search for crew links
            links = soup.find_all("a", href=True)
            job_links = []
            seen = set()

            for l in links:
                href = l["href"]
                text = l.text.strip()
                if not href:
                    continue

                # Check for career related paths in Polish/English
                is_career_link = any(
                    x in href.lower()
                    for x in [
                        "pilot",
                        "cabin-crew",
                        "job",
                        "career",
                        "recruitment",
                        "kariera",
                        "praca-w-samolocie",
                        "praca-w-biurze",
                        "operacje-lotnicze",
                    ]
                )

                if is_career_link:
                    if href not in seen:
                        seen.add(href)
                        if not href.startswith("http"):
                            href = (
                                "https://www.lot.com" + href
                                if href.startswith("/")
                                else "https://www.lot.com/" + href
                            )

                        # Only add if it's likely a specific job or a category page worth exploring
                        # Avoiding anchors and the main page
                        if "#" not in href and href != self.base_url:
                            job_links.append(
                                {"title": text or "Job Detail", "url": href}
                            )

            logger.info(
                f"[{self.site_key}] Found {len(job_links)} potential job links. Applying pre-filter..."
            )

            # PRE-FILTER: Filter by title first to skip irrelevant roles (like HR) COMPLETELY
            matched_links, _, _ = self.apply_title_filter(job_links)

            logger.info(
                f"[{self.site_key}] {len(matched_links)} jobs passed pre-filtering. Fetching details..."
            )

            for i, link_data in enumerate(matched_links):
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break

                try:
                    job_resp = requests.get(
                        link_data["url"], impersonate="chrome110", timeout=15
                    )
                    job_soup = BeautifulSoup(job_resp.content, "html.parser")

                    real_title = link_data["title"]
                    h1 = job_soup.find(
                        "h1", class_="hero-banner__title"
                    ) or job_soup.find("h1")
                    if h1 and h1.text.strip():
                        real_title = h1.text.strip()

                    description = ""
                    desc_elem = job_soup.find(
                        "div", class_=lambda c: c and "content" in c.lower()
                    )
                    if desc_elem:
                        description = str(desc_elem)
                    else:
                        description = (
                            str(job_soup.body) if job_soup.body else "Details in URL."
                        )

                    job_id = f"lot_{i + 1}"

                    job = get_job_dict(
                        job_id=job_id,
                        title=real_title,
                        company=self.company_name,
                        location="Poland",
                        url=link_data["url"],
                        source_url=self.base_url,
                        description=description,
                        apply_url=link_data["url"],
                        posted_date=None,
                        source=self.site_key,
                    )
                    jobs.append(job)

                except Exception as e:
                    logger.error(
                        f"[{self.site_key}] Error parsing {link_data['url']}: {e}"
                    )

        except Exception as e:
            logger.error(f"[{self.site_key}] Connection failed: {e}")

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
