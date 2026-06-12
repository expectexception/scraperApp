import logging
import requests
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

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
        """
        Scrape jobs from Sky Express career page
        """
        jobs = []

        try:
            logger.info(f"[{self.site_key}] Fetching jobs from {self.base_url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            
            resp = requests.get(self.base_url, headers=headers, timeout=30)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, 'html.parser')
            positions = soup.select('.position')

            logger.info(f"[{self.site_key}] Found {len(positions)} job cards on page")

            for i, pos_card in enumerate(positions):
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break

                title_tag = pos_card.find("h3")
                link_tag = pos_card.find("a")
                
                if not title_tag or not link_tag:
                    continue
                    
                title = title_tag.text.strip()
                url = link_tag.get("href", "").strip()
                
                if not url:
                    continue

                if not self.should_process_job(title):
                    continue

                # EForms don't have descriptions visible on the main page, so we use a placeholder
                desc = "Sky Express career opportunities. Please visit the official career portal to apply."
                
                # EForms don't specify location except sometimes in the title
                location = "Greece"
                if "Athens" in title:
                    location = "Athens, Greece"

                job_id = f"skyexpress_{hash(url)}"

                job = get_job_dict(
                    job_id=job_id,
                    title=title,
                    company=self.company_name,
                    location=location,
                    url=url,
                    source_url=self.base_url,
                    description=desc,
                    apply_url=url,
                    posted_date="",
                    source=self.site_key,
                )

                jobs.append(job)

        except Exception as e:
            logger.error(f"[{self.site_key}] Error scraping: {e}")
            import traceback
            logger.error(traceback.format_exc())

        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        jobs = [j for j in jobs if j is not None]

        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
