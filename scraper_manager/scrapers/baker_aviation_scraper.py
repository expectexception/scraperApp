import asyncio
import logging
import copy
from datetime import datetime
from typing import List, Dict, Any
from urllib.parse import urljoin

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class BakerAviationScraper(BaseScraper):
    """
    Scraper for Baker Aviation
    URL: https://www.baker-aviation.com/
    """

    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="baker_aviation", db_manager=db_manager)
        self.base_url = "https://www.baker-aviation.com/"
        self.company_name = "Baker Aviation"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Scrape jobs from Baker Aviation home/careers page
        """
        jobs = []
        logger.info(f"[{self.site_key}] Fetching page: {self.base_url}")
        
        response = await self.make_request(self.base_url)
        if not response or response.status_code != 200:
            logger.error(f"[{self.site_key}] Failed to load page: {self.base_url}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.select("div.career_card.positions")
        logger.info(f"[{self.site_key}] Found {len(cards)} job cards in HTML")

        for idx, card in enumerate(cards):
            if self.max_jobs and len(jobs) >= self.max_jobs:
                break

            # 1. Get Apply Link
            apply_btn = card.select_one("a.button, a.button-copy")
            apply_url = apply_btn.get("href") if apply_btn else self.base_url

            # 2. Get Title
            top = card.select_one(".career-card_top")
            if top:
                # Clone top element to avoid modifying the original tree
                top_clone = copy.copy(top)
                for btn in top_clone.select(".button, .button-copy"):
                    btn.decompose()
                title = top_clone.text.strip().replace("|", "").strip()
            else:
                title = "Unknown Open Position"

            # 3. Get Description (all other text in card positions)
            desc_parts = []
            for elem in card.children:
                if elem.name and elem.name == "div" and "career-card_top" not in elem.get("class", []):
                    desc_parts.append(elem.text.strip())
            description = "\n".join([p for p in desc_parts if p]).strip()

            if not description:
                description = f"Careers and opportunities under {title} at Baker Aviation."

            # Create clean job entry
            jobs.append({
                "job_id": f"baker_{idx}",
                "title": title,
                "company": self.company_name,
                "source": self.site_key,
                "url": self.base_url,
                "apply_url": apply_url,
                "description": description,
                "location": "Home Based / Remote",  # Standard fallback or parsed from description
                "posted_date": datetime.now().isoformat(),
            })

        logger.info(f"[{self.site_key}] Extracted {len(jobs)} jobs")
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

        # Skip duplicate filtering or let final save handle it
        await self.save_results(jobs)
        return jobs
