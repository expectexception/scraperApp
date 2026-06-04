import asyncio
import logging
import requests
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class SkyExpressScraper(BaseScraper):
    """
    Scraper for Sky Express
    URL: https://www.skyexpress.gr/en/company/careers
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="skyexpress", db_manager=db_manager)
        self.base_url = "https://www.skyexpress.gr/en/company/careers"
        self.company_name = "Sky Express"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Fetching Sky Express careers page...")

        try:
            resp = requests.get(self.base_url, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Find all position divs
            position_divs = soup.find_all("div", class_="position")
            logger.info(f"[{self.site_key}] Found {len(position_divs)} job entries")

            for div in position_divs:
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break

                title_elem = div.find("h3")
                if not title_elem:
                    continue

                title = title_elem.text.strip()

                link_elem = div.find("a", href=True)
                if not link_elem:
                    continue

                url = link_elem["href"]
                job_id = (
                    url.strip("/").split("/")[-2]
                    if len(url.strip("/").split("/")) > 2
                    else str(hash(url))
                )

                jobs.append(
                    {
                        "company": self.company_name,
                        "title": title,
                        "location": "Greece",  # Sky Express is Greece based
                        "url": url,
                        "source_url": self.base_url,
                        "apply_url": url,
                        "is_active": True,
                        "job_seq_no": job_id,
                    }
                )
        except Exception as e:
            logger.error(f"[{self.site_key}] Error fetching jobs: {e}")

        return jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        if not jobs:
            return []

        logger.info(
            f"[{self.site_key}] Fetching descriptions for {len(jobs)} matched jobs..."
        )

        for job in jobs:
            url = job["url"]

            try:
                resp = requests.get(url, timeout=20)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # Find main text container. Eforms often use body or specific divs.
                    content = soup.find("body")
                    if content:
                        # try to find the form div or content div
                        form_container = soup.find("div", class_="container") or content
                        text = form_container.text
                        import re

                        text = re.sub(r"\s+", " ", text).strip()
                        # Simple cleanup of eforms boilerplate
                        text = text.replace(
                            "Javascript is disabledJavascript is disabled on your browser. Please enable it in order to use this form. Loading",
                            "",
                        ).strip()
                        job["description"] = text
            except Exception as e:
                logger.warning(
                    f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}"
                )

            await asyncio.sleep(0.5)

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
