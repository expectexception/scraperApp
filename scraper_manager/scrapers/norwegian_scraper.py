import logging
import re
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class NorwegianScraper(BaseScraper):
    """
    Scraper for Norwegian Air Shuttle.
    URL: https://careers.norwegian.com/go/Administration/777902/
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="norwegian", db_manager=db_manager)
        self.base_url = "https://careers.norwegian.com/go/Administration/777902/"
        self.company_name = "Norwegian Air Shuttle"

    async def fetch_jobs(self) -> list:
        logger.info(
            f"[{self.site_key}] Navigating to {self.base_url} (Headless={self.headless})..."
        )
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(8000)
                await self.simulate_human_behavior(page)

                # Fetch job links and their location from the card layout
                extracted_jobs = await page.evaluate("""() => {
                    const rows = Array.from(document.querySelectorAll('div.job-row, tr.data-row'));
                    if (rows.length > 0) {
                        return rows.map(row => {
                            const a = row.querySelector('a.jobTitle-link');
                            if (!a) return null;
                            
                            // Find location element inside row
                            let locText = "";
                            const locEl = row.querySelector('[class*="location"], [class*="multilocation"]');
                            if (locEl) {
                                locText = locEl.innerText.trim()
                                    .replace("Other Locations", "")
                                    .replace("Location", "")
                                    .trim();
                            }
                            
                            return {
                                title: a.innerText.trim(),
                                href: a.href,
                                location: locText
                            };
                        }).filter(j => j !== null);
                    }
                    
                    // Fallback to simple links
                    return Array.from(document.querySelectorAll('a.jobTitle-link'))
                        .map(a => ({
                            title: a.innerText.trim(),
                            href: a.href,
                            location: ""
                        }));
                }""")

                logger.info(f"[{self.site_key}] Found {len(extracted_jobs)} potential jobs")

                seen_urls = set()
                for job_data in extracted_jobs:
                    url = job_data["href"]
                    title = job_data["title"]
                    location = job_data["location"]
                    
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    
                    if not self.should_process_job(title):
                        continue

                    # Refine location from URL slug if empty
                    if not location or location.lower() == "unknown" or location.lower() == "norway":
                        try:
                            path_parts = url.split("/job/")
                            if len(path_parts) > 1:
                                slug = path_parts[1].split("/")[0]
                                city = slug.split("-")[0]
                                location = city
                        except:
                            location = "Norway"

                    if await self.is_url_already_scraped(url):
                        continue

                    try:
                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break

                        logger.info(f"[{self.site_key}] Fetching details for: {url}")
                        detail_page = await context.new_page()
                        await detail_page.goto(
                            url, wait_until="domcontentloaded", timeout=30000
                        )
                        await detail_page.wait_for_timeout(2000)

                        real_title = title
                        h1 = detail_page.locator("h1").first
                        if await h1.is_visible():
                            extracted = await h1.inner_text()
                            if len(extracted) > 5:
                                real_title = extracted

                        description = ""
                        for loc in [
                            ".jobdescription",
                            ".content",
                            ".jo-job-description",
                            "main",
                        ]:
                            elem = detail_page.locator(loc).first
                            if await elem.is_visible():
                                description = await elem.inner_html()
                                break

                        if not description:
                            description = await self.extract_description_from_page(
                                detail_page
                            )

                        posted_date = await self.extract_posted_date_from_page(
                            detail_page
                        )

                        job_id = f"norwegian_{hash(url)}"
                        match = re.search(r"job/.*?/(\d+)", url)
                        if not match:
                            match = re.search(r"job-id=(\d+)", url)
                        if match:
                            job_id = f"norwegian_{match.group(1)}"

                        job = get_job_dict(
                            job_id=job_id,
                            title=real_title,
                            company=self.company_name,
                            location=location or "Norway",
                            url=url,
                            source_url=self.base_url,
                            description=description,
                            apply_url=url,
                            posted_date=posted_date,
                            source=self.site_key,
                        )

                        jobs.append(job)
                        await detail_page.close()

                    except Exception as e:
                        logger.error(
                            f"[{self.site_key}] Error parsing job detail ({url}): {e}"
                        )
                        continue

            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
            finally:
                await context.close()
                await browser.close()

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
