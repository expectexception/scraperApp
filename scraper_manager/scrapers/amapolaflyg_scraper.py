import logging
from datetime import datetime
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class AmapolaFlygScraper(BaseScraper):
    """
    Scraper for Amapola Flyg
    URL: https://amapola.nu/about-us/careers/
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="amapolaflyg", db_manager=db_manager)
        self.base_url = "https://www.populair.com/work-with-us/"
        self.company_name = "Amapola Flyg"

    async def fetch_jobs(self) -> list:
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")

                try:
                    await page.goto(
                        self.base_url, wait_until="networkidle", timeout=60000
                    )
                except Exception as e:
                    logger.error(f"[{self.site_key}] Navigation failed: {e}")
                    return []

                # Custom JS extraction since structure might vary
                jobs_data = await page.evaluate("""() => {
                    let results = [];
                    // Look for h3 or h2 under "OPEN POSITIONS" or similar sections
                    let headers = Array.from(document.querySelectorAll('h3, h2, h4'));
                    for (let h of headers) {
                        let title = h.innerText.trim();
                        if (title.length > 5 && title.toUpperCase() !== "OPEN POSITIONS" && title.toUpperCase() !== "CARREERS" && title.toUpperCase() !== "CONTACT") {
                            // Find corresponding text/link
                            let p = h.nextElementSibling;
                            let desc = "";
                            let link = window.location.href;
                            
                            while (p && !['H2','H3','H4'].includes(p.tagName)) {
                                desc += p.innerHTML || p.innerText;
                                let a = p.querySelector('a');
                                if (a && a.href && (a.href.includes('mailto') || a.href.includes('http'))) {
                                    if(!a.href.includes('mailto')) link = a.href;
                                }
                                p = p.nextElementSibling;
                            }
                            
                            if (desc.length > 10) {
                                results.push({title: title, desc: desc, link: link});
                            }
                        }
                    }
                    return results;
                }""")

                logger.info(
                    f"[{self.site_key}] Found {len(jobs_data)} jobs in listing. Applying pre-filter..."
                )

                # PRE-FILTER: Filter by title first to skip irrelevant roles COMPLETELY
                matched_data, _, _ = self.apply_title_filter(jobs_data)

                logger.info(
                    f"[{self.site_key}] {len(matched_data)} jobs passed pre-filtering."
                )

                for i, j_data in enumerate(matched_data):
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    job_id = f"amapola_{i + 1}"

                    job = get_job_dict(
                        job_id=job_id,
                        title=j_data["title"],
                        company=self.company_name,
                        location="Sweden",  # Amapola is normally based in Sweden
                        url=j_data["link"],
                        source_url=self.base_url,
                        description=j_data["desc"],
                        apply_url=j_data["link"],
                        posted_date=datetime.now().isoformat(),
                        source=self.site_key,
                    )
                    jobs.append(job)

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
