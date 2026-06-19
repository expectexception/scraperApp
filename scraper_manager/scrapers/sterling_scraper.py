import asyncio
import logging
import re
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class SterlingScraper(BaseScraper):
    """
    Scraper for Sterling Airways (flysterling.com)
    URL: https://flysterling.com/careers/
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="sterling", db_manager=db_manager)
        self.base_url = "https://flysterling.com/careers/"
        self.company_name = "Sterling Airways"

    async def fetch_jobs(self) -> list:
        all_jobs = []
        logger.info(f"[{self.site_key}] Fetching careers page: {self.base_url}")

        try:
            resp = await self.make_request(self.base_url)
            if not resp or resp.status_code != 200:
                logger.error(
                    f"[{self.site_key}] Failed to fetch page: Status {resp.status_code if resp else 'None'}"
                )
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            panels = soup.find_all(class_="vc_tta-panel")
            logger.info(f"[{self.site_key}] Found {len(panels)} jobs on page.")

            for panel in panels:
                title_elem = panel.find(class_="vc_tta-title-text")
                if not title_elem:
                    continue

                full_title = title_elem.text.strip()
                body_elem = panel.find(class_="vc_tta-panel-body")
                if not body_elem:
                    continue

                # Parse title and location
                parts = full_title.split(" - ")
                if len(parts) > 1:
                    title = parts[0].strip()
                    location = parts[1].strip()
                else:
                    title = full_title
                    location = "Global"

                # Extract apply URL
                a_tag = body_elem.find("a", href=True)
                apply_url = a_tag.get("href") if a_tag else self.base_url

                # Extract job ID
                job_id = "sterling_" + re.sub(r"\W+", "_", full_title).lower()
                if apply_url and "apply.appone.com/job/" in apply_url:
                    parts = apply_url.rstrip("/").split("/")
                    if parts:
                        job_id = f"sterling_{parts[-1]}"

                # Clean description
                description = self.clean_html(str(body_elem))

                job = get_job_dict(
                    job_id=job_id,
                    title=title,
                    company=self.company_name,
                    location=location,
                    url=self.base_url,
                    source_url=self.base_url,
                    description=description,
                    apply_url=apply_url,
                    source=self.site_key,
                )
                all_jobs.append(job)

        except Exception as e:
            logger.error(f"[{self.site_key}] Global error: {e}")

        return all_jobs

    def clean_html(self, html_content: str) -> str:
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, "html.parser")
        # Remove buttons or links if wanted, but text is fine
        text = soup.text
        text = re.sub(r"\s+", " ", text).strip()
        return text

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        jobs = [j for j in jobs if j is not None]

        if self.use_filter and self.filter_manager and jobs:
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
