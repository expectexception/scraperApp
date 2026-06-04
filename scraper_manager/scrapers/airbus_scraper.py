import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class AirbusScraper(BaseScraper):
    """
    Scraper for Airbus Jobs (Workday)

    Uses Internal Workday API:
    POST https://ag.wd3.myworkdayjobs.com/wday/cxs/ag/Airbus/jobs
    """

    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="airbus", db_manager=db_manager)
        self.base_url = "https://ag.wd3.myworkdayjobs.com/Airbus"
        self.api_url = "https://ag.wd3.myworkdayjobs.com/wday/cxs/ag/Airbus/jobs"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """
        Scrape jobs from Airbus Workday API (Listing only)
        """
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )

            try:
                logger.info(f"[{self.site_key}] Initializing session...")
                page = await context.new_page()
                try:
                    await page.goto(
                        self.base_url, wait_until="networkidle", timeout=60000
                    )
                except Exception:
                    logger.warning(
                        f"[{self.site_key}] Initial navigation timed out, continuing anyway"
                    )

                site_config = self.config.get("scrapers", {}).get("airbus", {})
                search_queries = site_config.get("search_queries", []) or [""]

                for query in search_queries:
                    if len(jobs) >= self.max_jobs:
                        break

                    logger.info(f"[{self.site_key}] Searching for: {query}")
                    offset = 0
                    limit = 20

                    while len(jobs) < self.max_jobs:
                        payload = {
                            "appliedFacets": {},
                            "limit": limit,
                            "offset": offset,
                            "searchText": query,
                        }

                        try:
                            response = await page.request.post(
                                self.api_url,
                                data=payload,
                                headers={
                                    "Content-Type": "application/json",
                                    "Accept": "application/json",
                                },
                            )

                            if response.status != 200:
                                break

                            data = await response.json()
                            job_items = data.get("jobPostings", [])
                            if not job_items:
                                break

                            logger.info(
                                f"[{self.site_key}] Found {len(job_items)} jobs (Offset: {offset})"
                            )

                            for item in job_items:
                                if len(jobs) >= self.max_jobs:
                                    break

                                external_path = item.get("externalPath") or ""
                                if external_path and not external_path.startswith("/"):
                                    external_path = "/" + external_path

                                job_id = item.get("bulletinId") or (
                                    external_path.split("/")[-1]
                                    if external_path
                                    else None
                                )
                                title = item.get("title") or "Unknown Title"

                                url = (
                                    f"https://ag.wd3.myworkdayjobs.com/Airbus{external_path}"
                                    if external_path
                                    else self.base_url
                                )

                                # Parse the posted date from the relative string (e.g. "Posted 4 Days Ago")
                                raw_posted = item.get("postedOn", "")
                                parsed_posted = (
                                    self.parse_posted_date(raw_posted)
                                    if raw_posted
                                    else None
                                )

                                jobs.append(
                                    {
                                        "company": self.company_name,
                                        "title": title.strip(),
                                        "location": item.get(
                                            "locationsText", ""
                                        ).strip(),
                                        "url": url.strip(),
                                        "apply_url": f"{url.strip()}/apply",
                                        "posted_date": parsed_posted,
                                        "job_id": job_id.strip() if job_id else None,
                                    }
                                )

                            offset += limit
                            await asyncio.sleep(0.5)
                        except Exception as e:
                            logger.error(
                                f"[{self.site_key}] Error fetching offset {offset}: {e}"
                            )
                            break
            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
            finally:
                await browser.close()

        return jobs

    async def fetch_job_descriptions(
        self, jobs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Fetch full details for matched jobs only"""
        if not jobs:
            return []

        logger.info(
            f"[{self.site_key}] Fetching descriptions for {len(jobs)} matched jobs..."
        )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()

            for job in jobs:
                if not job.get("job_id"):
                    continue
                try:
                    import urllib.parse

                    safe_job_id = urllib.parse.quote(job["job_id"].strip())
                    desc_url = f"https://ag.wd3.myworkdayjobs.com/wday/cxs/ag/Airbus/job/{safe_job_id}"
                    resp = await page.request.get(desc_url)
                    if resp.status == 200:
                        desc_data = await resp.json()
                        info = desc_data.get("jobPostingInfo", {})
                        job["description"] = info.get("jobDescription")
                        # Prefer the ISO date from the detail API; fall back to listing date
                        raw_detail_date = info.get("postedOn") or info.get("datePosted")
                        if raw_detail_date:
                            parsed = self.parse_posted_date(str(raw_detail_date))
                            if parsed:
                                job["posted_date"] = parsed
                        job["employment_type"] = info.get("timeType")
                        job["job_category"] = info.get("jobCategory")
                except Exception as e:
                    logger.warning(
                        f"[{self.site_key}] Failed to fetch description for {job['job_id']}: {e}"
                    )
                await asyncio.sleep(0.3)

            await browser.close()
        return jobs

    async def run(self):
        """Main execution method"""
        self.print_header()

        # Step 1: Discovery
        jobs = await self.fetch_jobs()
        if not jobs:
            return []

        # Step 2: Pre-filtering (The "Only Scrape Matches" requirement)
        if self.use_filter and self.filter_manager:
            logger.info(f"[{self.site_key}] Applying pre-filter...")
            matched_jobs, rejected_jobs, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

            if not matched_jobs:
                logger.info(f"[{self.site_key}] No jobs matched filter criteria.")
                return []
            jobs = matched_jobs

        # Step 3: Duplicate Check
        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []

        # Step 4: Enrichment
        jobs = await self.fetch_job_descriptions(jobs)

        # Step 5: Save
        await self.save_results(jobs)
        return jobs
