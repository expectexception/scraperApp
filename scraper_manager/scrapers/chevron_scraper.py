import asyncio
import logging
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

LIST_URL = "https://careers.chevron.com/category/aviation-jobs/35016/8307184/1"
BASE_URL = "https://careers.chevron.com"


class ChevronScraper(BaseScraper):
    """
    Scraper for Chevron Aviation Jobs (static HTML)
    URL: https://careers.chevron.com/category/aviation-jobs/35016/8307184/1
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="chevron", db_manager=db_manager)
        self.base_url = LIST_URL
        self.company_name = "Chevron"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Scraping Chevron aviation job listings...")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        try:
            resp = await self.make_request(LIST_URL, method="GET", headers=headers, timeout=20)
            if not resp or resp.status_code != 200:
                logger.warning(f"[{self.site_key}] Failed to fetch list page: {resp.status_code if resp else 'None'}")
                return jobs

            soup = BeautifulSoup(resp.text, "html.parser")
            # Job links are in <a href="/job/..."> elements
            job_links = soup.select("a[href^='/job/']")

            seen_urls = set()
            for link in job_links:
                href = link.get("href", "")
                if not href or href in seen_urls:
                    continue
                seen_urls.add(href)

                title = link.get_text(strip=True)
                if not title:
                    # Try getting title from nearby elements
                    parent = link.find_parent(["li", "div", "article"])
                    if parent:
                        title = parent.get_text(strip=True)[:80]

                job_url = f"{BASE_URL}{href}"
                jobs.append(
                    {
                        "company": self.company_name,
                        "title": title,
                        "location": "Unknown",
                        "url": job_url,
                        "source_url": job_url,
                        "apply_url": job_url,
                        "is_active": True,
                    }
                )

        except Exception as e:
            logger.error(f"[{self.site_key}] Failed to fetch job list: {e}")

        logger.info(f"[{self.site_key}] Found {len(jobs)} jobs")
        return jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        if not jobs:
            return []

        logger.info(
            f"[{self.site_key}] Fetching descriptions for {len(jobs)} jobs..."
        )
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        enriched = []

        async def fetch_detail(job):
            try:
                resp = await self.make_request(
                    job["url"], method="GET", headers=headers, timeout=20
                )
                if resp and resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")

                    # Get title from page
                    title_el = soup.select_one("h1, h2.job-title, .job-title")
                    if title_el:
                        job["title"] = title_el.get_text(strip=True)

                    # Get location
                    loc_el = soup.select_one(".job-location, [class*='location']")
                    if loc_el:
                        job["location"] = loc_el.get_text(strip=True)

                    # Fallback location from URL
                    if not job.get("location") or job.get("location") == "Unknown":
                        parts = job["url"].split("/job/")
                        if len(parts) > 1:
                            sub_parts = parts[1].split("/")
                            if sub_parts and sub_parts[0]:
                                job["location"] = sub_parts[0].replace("-", " ").title()

                    # Get description
                    desc_el = soup.select_one(".job-description, .description, main article, .content")
                    if desc_el:
                        job["description"] = desc_el.get_text(" ", strip=True)[:5000]

            except Exception as e:
                logger.warning(
                    f"[{self.site_key}] Failed detail fetch for {job['title']}: {e}"
                )

        chunk_size = 5
        for i in range(0, len(jobs), chunk_size):
            chunk = jobs[i : i + chunk_size]
            await asyncio.gather(*(fetch_detail(job) for job in chunk))
            await asyncio.sleep(0.5)

        for job in jobs:
            job_dict = get_job_dict(
                job_id=f"{self.site_key}_{hash(job['url'])}",
                title=job["title"],
                company=job["company"],
                location=job.get("location", "Unknown"),
                url=job["url"],
                source_url=self.base_url,
                description=job.get("description", ""),
                apply_url=job["url"],
                source=self.site_key,
            )
            enriched.append(job_dict)

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
