import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class FlyTropicScraper(BaseScraper):
    """
    Scraper for Tropic Ocean Airways
    URL: https://flytropic.com/careers-full-description-and-applications/
    """
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__(config, site_key="flytropic", db_manager=db_manager)
        self.base_url = "https://flytropic.com/careers-full-description-and-applications/"
        self.company_name = "Tropic Ocean Airways"

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            try:
                logger.info(f"[{self.site_key}] Navigating to {self.base_url}...")
                await page.goto(self.base_url, wait_until="networkidle", timeout=60000)
                await self.random_delay(2, 4)

                # This careers page has no per-job URLs: every role (Pilot,
                # Logistics Assistant, Operations Coordinator, etc.) is listed
                # inline as a "qode-accordion-holder" block with the title in
                # ".qode-tab-title-inner" and the description in
                # ".qode-accordion-content-inner". Application links (PDF /
                # airlineapps.com) are shared across all roles, so we use the
                # careers page itself as the job URL and dedupe by title.
                postings = await page.evaluate('''() => {
                    // The page has two ".qode-accordion-holder" sections
                    // ("Job Summaries" and "Application Process"). Within
                    // each, every role/step is a flat sibling pair: an
                    // "h4.qode-title-holder" (title) immediately followed by
                    // a ".qode-accordion-content" (description) -- there is
                    // no per-job wrapper element. Use the first holder
                    // (job summaries) only.
                    const holders = document.querySelectorAll(".qode-accordion-holder");
                    if (!holders.length) return [];
                    const jobHolder = holders[0];
                    const results = [];
                    const headers = jobHolder.querySelectorAll("h4.qode-title-holder");
                    headers.forEach(h => {
                        const titleEl = h.querySelector(".qode-tab-title-inner");
                        const contentEl = h.nextElementSibling;
                        const descEl = contentEl ? contentEl.querySelector(".qode-accordion-content-inner") : null;
                        results.push({
                            title: titleEl ? titleEl.innerText.trim() : "",
                            description: descEl ? descEl.innerText.trim() : ""
                        });
                    });
                    return results;
                }''')

                for posting in postings:
                    if self.max_jobs and len(jobs) >= self.max_jobs: break
                    try:
                        text = (posting.get("title") or "").strip()
                        if len(text) < 3: continue
                        if text.lower() in ["interview process", "orientation", "equal employment opportunity", "application process"]:
                            continue

                        job_url = self.base_url
                        job_id = f"flytropic_{abs(hash(text)) % 10000000}"
                        jobs.append({
                            "job_id": job_id,
                            "title": text,
                            "company": self.company_name,
                            "source": self.site_key,
                            "url": job_url,
                            "apply_url": job_url,
                            "location": "USA",
                            "description": posting.get("description", ""),
                        })
                    except:
                        continue
            except Exception as e:
                logger.error(f"[{self.site_key}] Global error: {e}")
            finally:
                await context.close()
                await browser.close()
        return jobs

    async def fetch_job_descriptions(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not jobs: return []
        # All roles share a single careers page (no per-job URL); the
        # description for each was already captured from its accordion
        # block in fetch_jobs, so skip re-navigating for those.
        jobs_needing_fetch = [j for j in jobs if not j.get("description")]
        if not jobs_needing_fetch:
            return jobs
        logger.info(f"[{self.site_key}] Fetching descriptions for {len(jobs_needing_fetch)} matched jobs...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            for job in jobs_needing_fetch:
                try:
                    page, context = await self.setup_stealth_page(browser)
                    await page.goto(job["url"], wait_until="domcontentloaded", timeout=30000)
                    desc = ""
                    selectors = [".elementor-widget-theme-post-content", ".entry-content", ".content", "main"]
                    for sel in selectors:
                        el = await page.query_selector(sel)
                        if el:
                            text = await el.inner_text()
                            if len(text) > 100:
                                desc = text.strip()
                                break
                    if not desc:
                        desc = await self.extract_description_from_page(page)
                    job["description"] = desc
                    # Backfill location from the original posting when missing.
                    if not job.get("location") or job.get("location") == "Unknown":
                        _loc = await self.extract_location_from_page(page)
                        if _loc:
                            job["location"] = _loc
                except Exception as e:
                    logger.warning(f"[{self.site_key}] Failed to fetch details for {job['title']}: {e}")
                finally:
                    await context.close()
                await asyncio.sleep(1)
            await browser.close()
        return jobs

    async def run(self):
        self.print_header()
        jobs_raw = await self.fetch_jobs()
        jobs = [get_job_dict(**job) for job in jobs_raw]
        if not jobs: return []
        if self.use_filter and self.filter_manager:
            jobs, _, _ = self.apply_title_filter(jobs)
            if not jobs: return []
        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs: return []
        jobs = await self.fetch_job_descriptions(jobs)
        await self.save_results(jobs)
        return jobs
