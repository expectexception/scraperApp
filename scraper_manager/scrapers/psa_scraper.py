import asyncio
import logging
import requests
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class PsaScraper(BaseScraper):
    """
    Scraper for PSA Airlines (iCIMS)
    URL: https://careers-psaairlines.icims.com/jobs/search?in_iframe=1
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="psa", db_manager=db_manager)
        self.base_url = "https://careers-psaairlines.icims.com/jobs/search?in_iframe=1"
        self.company_name = "PSA Airlines"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Fetching PSA Airlines jobs...")

        page = 0
        while True:
            if self.max_pages and page >= self.max_pages:
                break

            url = f"{self.base_url}&pr={page}"
            logger.info(f"[{self.site_key}] Fetching page {page}: {url}")
            try:
                resp = requests.get(
                    url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30
                )
                if resp.status_code != 200:
                    break

                soup = BeautifulSoup(resp.text, "html.parser")
                rows = soup.find_all("div", class_="row")

                # Check if there are no more jobs (some rows are not jobs, so check for iCIMS_Anchor)
                job_anchors = soup.find_all("a", class_="iCIMS_Anchor")
                if not job_anchors:
                    break

                found_new = False
                for row in rows:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    a = row.find("a", class_="iCIMS_Anchor")
                    if not a:
                        continue

                    href = a.get("href")
                    if not href or "job" not in href:
                        continue

                    found_new = True
                    # Clean title: usually h3 inside a
                    h3 = a.find("h3")
                    title = h3.text.strip() if h3 else a.text.strip()
                    # iCIMS often has prefix like "Title\n\nAircraft Dispatch Coordinator", or sr-only tags
                    for sr in a.find_all("span", class_="sr-only"):
                        sr.decompose()
                    title = a.text.strip().replace("\n", " ").strip()

                    location = "Unknown"
                    loc_label = row.find(string=lambda t: t and "Job Locations" in t)
                    if loc_label:
                        parent_div = loc_label.find_parent("div")
                        if parent_div:
                            spans = parent_div.find_all("span")
                            if len(spans) > 1:
                                location = spans[1].text.strip()
                            else:
                                location = spans[-1].text.strip()

                    job_id = "unknown"
                    id_tag = row.find("dt", string="ID")
                    if id_tag:
                        dd = id_tag.find_next_sibling("dd")
                        if dd:
                            job_id = dd.text.strip()
                    else:
                        job_id = (
                            href.split("/")[-3] if len(href.split("/")) > 3 else href
                        )

                    # Remove in_iframe=1 for the apply url if needed, or keep it
                    apply_url = href.replace("?in_iframe=1", "")

                    jobs.append(
                        {
                            "company": self.company_name,
                            "title": title,
                            "location": location,
                            "url": href,
                            "source_url": self.base_url,
                            "apply_url": apply_url,
                            "is_active": True,
                            "job_seq_no": job_id,
                        }
                    )

                if not found_new:
                    break

            except Exception as e:
                logger.error(f"[{self.site_key}] Error fetching page {page}: {e}")
                break

            page += 1
            await asyncio.sleep(1)

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
                resp = requests.get(
                    url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20
                )
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    content = soup.find("div", class_="iCIMS_JobContent")
                    if content:
                        import re

                        text = re.sub(r"\s+", " ", content.text).strip()
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
