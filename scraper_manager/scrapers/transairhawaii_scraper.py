import asyncio
import logging
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

BASE_URL = "https://transairhawaii.com"
JOBS_URL = f"{BASE_URL}/category/jobs/"


class TransairHawaiiScraper(BaseScraper):
    """
    Scraper for Transair Cargo Hawaii (WordPress blog-based job posts)
    URL: https://transairhawaii.com/category/jobs/
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="transairhawaii", db_manager=db_manager)
        self.base_url = JOBS_URL
        self.company_name = "Transair"

    async def fetch_jobs(self) -> list:
        jobs = []
        page = 1
        logger.info(f"[{self.site_key}] Scraping Transair job listings...")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        while True:
            url = f"{JOBS_URL}page/{page}/" if page > 1 else JOBS_URL

            try:
                resp = await self.make_request(url, method="GET", headers=headers, timeout=20)
                if not resp or resp.status_code != 200:
                    break

                soup = BeautifulSoup(resp.text, "html.parser")
                posts = soup.select("div.post")

                if not posts:
                    break

                for post in posts:
                    title_el = post.select_one("h2.title a")
                    if not title_el:
                        continue

                    title = title_el.get_text(strip=True)
                    job_url = title_el.get("href", "")

                    # Get location from post content if available
                    content_el = post.select_one(".post-content")
                    content_text = content_el.get_text(" ", strip=True)[:500] if content_el else ""

                    jobs.append(
                        {
                            "company": self.company_name,
                            "title": title,
                            "location": "Hawaii, USA",
                            "url": job_url,
                            "source_url": job_url,
                            "apply_url": job_url,
                            "is_active": True,
                            "description": content_text,
                        }
                    )

                # Check for next page link
                next_link = soup.select_one("a.next.page-numbers")
                if not next_link:
                    break
                page += 1

            except Exception as e:
                logger.error(f"[{self.site_key}] Error scraping page {page}: {e}")
                break

        logger.info(f"[{self.site_key}] Found {len(jobs)} total jobs")
        return jobs

    async def fetch_job_descriptions(self, jobs) -> list:
        if not jobs:
            return []

        logger.info(
            f"[{self.site_key}] Fetching full descriptions for {len(jobs)} jobs..."
        )
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        enriched = []
        for job in jobs:
            try:
                resp = await self.make_request(
                    job["url"], method="GET", headers=headers, timeout=15
                )
                if resp and resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    content = soup.select_one(".post-content, .entry-content, article")
                    if content:
                        job["description"] = content.get_text(" ", strip=True)[:3000]
            except Exception as e:
                logger.warning(
                    f"[{self.site_key}] Failed to fetch detail for {job['title']}: {e}"
                )

            job_dict = get_job_dict(
                job_id=f"{self.site_key}_{hash(job['url'])}",
                title=job["title"],
                company=job["company"],
                location=job["location"],
                url=job["url"],
                source_url=self.base_url,
                description=job.get("description", ""),
                apply_url=job["url"],
                source=self.site_key,
            )
            enriched.append(job_dict)
            await asyncio.sleep(0.3)

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
