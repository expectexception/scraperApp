import logging
import re
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class KalittaAirScraper(BaseScraper):
    """
    Scraper for Kalitta Air (ADP Workforce Now)
    URL: https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?ccId=19000101_000001&cid=17b87f3e-11d6-434a-b3df-0d83d72f832b&lang=en_US&type=MP
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="kalitta_air", db_manager=db_manager)
        self.base_url = "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?ccId=19000101_000001&cid=17b87f3e-11d6-434a-b3df-0d83d72f832b&lang=en_US&type=MP"
        self.api_base_url = "https://workforcenow.adp.com/mascsr/default/careercenter/public/events/staffing/v1"
        self.cid = "17b87f3e-11d6-434a-b3df-0d83d72f832b"
        self.ccid = "19000101_000001"
        self.company_name = "Kalitta Air"

    async def fetch_jobs(self) -> list:
        all_jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                # 1. Establish session
                logger.info(
                    f"[{self.site_key}] Establishing session at {self.base_url}..."
                )
                await page.goto(self.base_url, wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(5000)

                # 2. Call ADP API via evaluate to use session cookies
                skip = 0
                top = 20
                while True:
                    if self.max_jobs and len(all_jobs) >= self.max_jobs:
                        break

                    api_url = f"{self.api_base_url}/job-requisitions?cid={self.cid}&ccId={self.ccid}&lang=en_US&$top={top}&$skip={skip}"
                    logger.info(f"[{self.site_key}] Fetching API: {api_url}")

                    response_json = await page.evaluate(f'''async () => {{
                        const res = await fetch("{api_url}");
                        return await res.json();
                    }}''')

                    requisitions = response_json.get("jobRequisitions", [])
                    if not requisitions:
                        logger.info(f"[{self.site_key}] No more jobs found in API.")
                        break

                    logger.info(
                        f"[{self.site_key}] Found {len(requisitions)} jobs in current API chunk."
                    )

                    for req in requisitions:
                        if self.max_jobs and len(all_jobs) >= self.max_jobs:
                            break

                        title = req.get("requisitionTitle", "")
                        item_id = req.get("itemID", "")
                        posted_date_raw = req.get("postDate", "")

                        # Extract location
                        loc_obj = req.get("workLocation", {})
                        location = "USA"
                        if loc_obj:
                            city = loc_obj.get("cityName", "")
                            state = loc_obj.get("stateProvinceCode", "")
                            country = loc_obj.get("countryCode", "")
                            location = f"{city}, {state}, {country}".strip(", ")

                        url = f"{self.base_url}&jobId={item_id}"

                        if not self.should_process_job(title):
                            continue

                        if await self.is_url_already_scraped(url):
                            continue

                        # 3. Fetch Job Detail
                        try:
                            # Use the detail API for the description
                            detail_api_url = f"{self.api_base_url}/job-requisitions/{item_id}?cid={self.cid}&ccId={self.ccid}&lang=en_US"
                            logger.info(
                                f"[{self.site_key}] Fetching detail API for: {item_id}"
                            )

                            detail_json = await page.evaluate(f'''async () => {{
                                const res = await fetch("{detail_api_url}");
                                return await res.json();
                            }}''')

                            description_html = detail_json.get(
                                "requisitionDescription", ""
                            )
                            description = self.clean_html(description_html)

                            posted_date = self.parse_posted_date(posted_date_raw)

                            job = get_job_dict(
                                job_id=f"kalitta_{item_id}",
                                title=title,
                                company=self.company_name,
                                location=location,
                                url=url,
                                source_url=self.base_url,
                                description=description,
                                apply_url=url,
                                posted_date=posted_date,
                                source=self.site_key,
                            )

                            all_jobs.append(job)
                            await self.random_delay(1, 2)

                        except Exception as e:
                            logger.error(
                                f"[{self.site_key}] Error fetching detail for {item_id}: {e}"
                            )
                            continue

                    skip += top
                    if len(requisitions) < top:
                        break

            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
            finally:
                await context.close()
                await browser.close()

        return all_jobs

    def clean_html(self, html: str) -> str:
        """Simple HTML cleaner for ADP descriptions"""
        if not html:
            return ""
        # Remove tags
        clean = re.sub(r"<[^>]*>", " ", html)
        # Fix entities
        clean = (
            clean.replace("&nbsp;", " ")
            .replace("&amp;", "&")
            .replace("&gt;", ">")
            .replace("&lt;", "<")
        )
        # Fix whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

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
