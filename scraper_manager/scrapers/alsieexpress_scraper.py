import asyncio
import logging
import re
from playwright.async_api import async_playwright

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class AlsieExpressScraper(BaseScraper):
    """
    Scraper for Alsie Express.
    Currently, they do not have an active ATS or published careers section, 
    only a spontaneous contact page. Safely returns empty.
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='alsieexpress', db_manager=db_manager)
        self.jobs_url = "https://candidate.hr-manager.net/vacancies/list.aspx?customer=alsie_tr&nocookie=true&uiculture=en"
        self.domain = "https://candidate.hr-manager.net"
        self.company_name = "Alsie Express"

    async def fetch_jobs(self) -> list:
        logger.info(f"[{self.site_key}] Fetching jobs from listing...")
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
                print(f"Loading {self.company_name} careers page...")
                await self.random_delay(1, 2)
                await page.goto(self.jobs_url, wait_until='domcontentloaded', timeout=45000)

                await self.random_delay(2, 4)
                await self.simulate_human_behavior(page)

                # Extract from HR manager header rows
                job_links = await page.evaluate('''() => {
                    let rows = Array.from(document.querySelectorAll('.header_row'));
                    return rows.map(r => {
                        let title = r.getAttribute('data-position') || '';
                        let loc = r.getAttribute('data-location') || 'Unknown';
                        let onclick = r.getAttribute('onclick');
                        let urlMatch = onclick ? onclick.match(/'([^']+)'/) : null;
                        let href = urlMatch ? urlMatch[1] : '';
                        return { title: title.trim(), location: loc.trim(), href: href };
                    }).filter(x => x.href && x.title);
                }''')
                
                print(f"✓ Found {len(job_links)} jobs")

                if not job_links:
                    return jobs

                for l in job_links[:self.max_jobs] if self.max_jobs else job_links:
                    try:
                        title = l['title']
                        if not self.should_process_job(title):
                            continue
                            
                        href = l['href']
                        job_url = href if href.startswith('http') else f"https://candidate.hr-manager.net/vacancies/{href.lstrip('/')}"
                        
                        job_id = None
                        match = re.search(r'vacancyId=(\d+)', job_url)
                        if match:
                            job_id = match.group(1)
                        if not job_id:
                            job_id = f"alsie_{len(jobs) + 1}"

                        job_data = {
                            'job_id': f"alsie_{job_id}",
                            'title': l['title'],
                            'company': self.company_name,
                            'source': self.site_key,
                            'url': job_url,
                            'apply_url': job_url,
                            'location': self.normalize_location(l['location']),
                        }
                        jobs.append(job_data)
                    except Exception as e:
                        print(f"Error parsing job link {l}: {e}")
                        continue

            except Exception as e:
                print(f"❌ Error fetching jobs: {e}")
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
        print(f"✓ Successfully extracted {with_desc}/{len(jobs)} descriptions")

        return jobs

    async def _extract_description(self, browser, job):
        try:
            page, context = await self.setup_stealth_page(browser)
            await self.random_delay(1, 2)
            await page.goto(job['url'], wait_until='domcontentloaded', timeout=45000)
            await self.random_delay(2, 4)
            await self.simulate_human_behavior(page)

            # Detail title
            title_elem = await page.query_selector('.ProjectName')
            if title_elem:
                title_text = await title_elem.inner_text()
                if title_text and len(title_text) > 3:
                    job['title'] = title_text.strip()

            desc_selectors = ['.layer', 'main', '.content']
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
            print(f"  Error fetching description for {job['job_id']}: {e}")
