import asyncio
import logging
import re
from datetime import datetime
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

class AirFranceScraper(BaseScraper):
    """Scraper for Air France Recruitment"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, 'airfrance', db_manager=db_manager)
        self.site_config = config.get('sites', {}).get('airfrance', {})
        self.base_url = self.site_config.get('base_url', 'https://recrutement.airfrance.com')
        # We start by hitting the main job search page or the "All Jobs" endpoint if possible. 
        # For simplicity, we can hit a general search URL that returns all results
        self.jobs_url = self.site_config.get('jobs_url', 'https://recrutement.airfrance.com/accueil.aspx?LCID=2057')
        self.company_name = "Air France"

    async def fetch_jobs(self) -> list:
        self.logger.info(f"[{self.site_key}] Fetching jobs from listing...")
        jobs_raw = await self._fetch_jobs_listing()
        jobs = [get_job_dict(**job) for job in jobs_raw]

        if not jobs:
            return []

        jobs_with_descriptions = await self.fetch_job_descriptions(jobs)
        return jobs_with_descriptions

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        
        if self.use_filter and self.filter_manager:
            matched_jobs, rejected_jobs, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)
            jobs = matched_jobs

        jobs, duplicate_count = await self.filter_new_jobs(jobs)
        await self.save_results(jobs)
        self.print_sample(jobs)
        return jobs

    async def _fetch_jobs_listing(self):
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                self.logger.info(f"[{self.site_key}] Loading {self.company_name} careers page...")
                await self.random_delay(1, 2)
                await page.goto(self.jobs_url, wait_until='domcontentloaded', timeout=45000)

                await self.random_delay(4, 6)
                await self.simulate_human_behavior(page)

                job_links = await page.evaluate('''() => {
                    let links = Array.from(document.querySelectorAll('a'));
                    return links.filter(a => a.href.includes('/job/') && a.innerText.trim().length > 3).map(a => ({
                        href: a.href,
                        title: a.innerText.trim()
                    }));
                }''')
                
                # Check for "Search Offers" page if the main url didn't yield many
                if len(job_links) < 5:
                    await page.goto("https://recrutement.airfrance.com/offre-de-emploi/liste-offres.aspx", wait_until='domcontentloaded')
                    await self.random_delay(2, 4)
                    more_links = await page.evaluate('''() => {
                        let links = Array.from(document.querySelectorAll('a'));
                        return links.filter(a => a.href.includes('/offre-de-emploi/emploi-') || a.href.includes('/job/job-')).map(a => ({
                            href: a.href,
                            title: a.innerText.trim()
                        }));
                    }''')
                    job_links.extend(more_links)

                unique_links = {}
                for l in job_links:
                    if l['href'] not in unique_links and l['title']:
                        unique_links[l['href']] = l['title']

                self.logger.info(f"[{self.site_key}] ✓ Found {len(unique_links)} jobs")

                if not unique_links:
                    return jobs

                for href, title in list(unique_links.items())[:self.max_jobs] if self.max_jobs else unique_links.items():
                    try:
                        job_url = href if href.startswith('http') else f"{self.base_url}{href}"
                        
                        job_id = None
                        match = re.search(r'_(\d+)\.aspx', job_url)
                        if match:
                            job_id = match.group(1)
                        if not job_id:
                            job_id = f"airfrance_{len(jobs) + 1}"

                        job_data = {
                            'job_id': f"airfrance_{job_id}",
                            'title': title,
                            'company': self.company_name,
                            'source': self.site_key,
                            'url': job_url,
                            'apply_url': job_url,
                            'location': 'Unknown',
                            'timestamp': datetime.now().isoformat(),
                        }
                        jobs.append(job_data)
                    except Exception as e:
                        continue

            except Exception as e:
                self.logger.error(f"[{self.site_key}] ❌ Error fetching jobs: {e}")
            finally:
                await context.close()
                await browser.close()
        return jobs

    async def fetch_job_descriptions(self, jobs):
        print(f"\nFetching detailed descriptions for {len(jobs)} jobs...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)

            for i in range(0, len(jobs), self.batch_size):
                batch = jobs[i:i + self.batch_size]
                tasks = []

                for job in batch:
                    if job.get('url'):
                        tasks.append(self._extract_description(browser, job))

                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

                print(f"  Processed {min(i + self.batch_size, len(jobs))}/{len(jobs)} jobs")

            await browser.close()

        with_desc = sum(1 for job in jobs if job.get('description'))
        self.logger.info(f"[{self.site_key}] ✓ Successfully extracted {with_desc}/{len(jobs)} descriptions")

        return jobs

    async def _extract_description(self, browser, job):
        try:
            page, context = await self.setup_stealth_page(browser)
            await self.random_delay(1, 2)
            await page.goto(job['url'], wait_until='load', timeout=30000)
            await self.random_delay(2, 4)
            await self.simulate_human_behavior(page)

            # Air France specific structure
            location_selectors = ['.offer-location', '.job-location', '.location', '.localite']
            for selector in location_selectors:
                try:
                    loc_elem = await page.query_selector(selector)
                    if loc_elem:
                        loc_text = await loc_elem.inner_text()
                        if loc_text and len(loc_text) > 2:
                            job['location'] = loc_text.strip()
                            break
                except Exception:
                    continue

            desc_selectors = ['.offer-description', '.job-description', '.content-text', 'main', '.blocText']
            description = ''
            for selector in desc_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        text = await elem.inner_text()
                        if text and len(text) > 100:
                            description = text.strip()
                            break
                except Exception:
                    continue

            if not description:
                description = await self.extract_description_from_page(page)

            posted_date = await self.extract_posted_date_from_page(page)
            if posted_date:
                job['posted_date'] = posted_date

            job['description'] = description

            await page.close()
            await context.close()

        except Exception as e:
            self.logger.warning(f"[{self.site_key}]  Error fetching description for {job['job_id']}: {e}")
