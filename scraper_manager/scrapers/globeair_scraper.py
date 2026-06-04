import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class GlobeAirScraper(BaseScraper):
    """
    Scraper for GlobeAir Careers
    URL: https://www.globeair.com/career
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="globeair", db_manager=db_manager)
        self.base_url = "https://www.globeair.com/career"
        self.company_name = "GlobeAir"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Fetching GlobeAir careers page...")

        try:
            resp = requests.get(self.base_url, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            links = soup.find_all("a")
            for a in links:
                href = a.get("href", "")
                if "globeair.com/j/" in href:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    parent = a.find_parent("div")
                    # Usually the title is the first text block in the parent
                    # For example an h3 or h4
                    title_elem = parent.find(["h3", "h4", "h5", "strong"])
                    if title_elem:
                        title = title_elem.text.strip()
                    else:
                        # Fallback: extract the text before 'View opportunity'
                        text_blocks = [
                            t
                            for t in parent.stripped_strings
                            if "opportunity" not in t.lower() and t != "→"
                        ]
                        title = (
                            text_blocks[0] if text_blocks else "GlobeAir Opportunity"
                        )

                    url = href
                    job_id = url.split("/")[-1]

                    jobs.append(
                        {
                            "company": self.company_name,
                            "title": title,
                            "location": "Europe/Austria",  # GlobeAir is mostly Austria based (Linz)
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
            job.pop("job_seq_no", None)
            url = job["url"]

            try:
                resp = requests.get(url, timeout=20)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # Just grab the main body of the job description, often in a container
                    content_div = (
                        soup.find("div", class_="content")
                        or soup.find("main")
                        or soup.find("body")
                    )
                    if content_div:
                        job["description"] = content_div.text.strip()
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
            jobs, _, _ = self.apply_title_filter(jobs)
            if not jobs:
                return []

        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []

        jobs = await self.fetch_job_descriptions(jobs)
        await self.save_results(jobs)
        return jobs
