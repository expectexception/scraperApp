import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict
import re

class AegeanScraper(BaseScraper):
    """Scraper for Aegean Airlines Careers (SuccessFactors)"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, 'aegean', db_manager=db_manager)
        self.site_config = config.get('sites', {}).get('aegean', {})
        self.base_url = self.site_config.get('base_url', 'https://jobs.aegeanair.com')
        # Point to the View All Jobs page for Aegean SuccessFactors
        self.jobs_url = self.base_url + '/go/All-Jobs/8966755/'
        self.company_name = "Aegean Airlines"

    async def run(self):
        """Main execution method"""
        self.print_header()

        print(f"Fetching jobs from {self.company_name}...")
        print(f"URL: {self.jobs_url}\n")

        jobs_raw = await self.fetch_jobs_from_listing()
        jobs = [get_job_dict(**job) for job in jobs_raw]

        if not jobs:
            print("❌ No jobs found")
            return []

        print(f"\n✓ Extracted {len(jobs)} jobs from listing")

        # Apply title filtering BEFORE fetching descriptions
        if self.use_filter and self.filter_manager:
            print(f"\n🔍 Applying title filter...")
            matched_jobs, rejected_jobs, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

            if not matched_jobs:
                print("❌ No jobs matched the filter criteria")
                return []
            jobs = matched_jobs

        # Filter duplicates
        jobs, duplicate_count = await self.filter_new_jobs(jobs)
        if duplicate_count > 0:
            print(f"\n🔄 Filtered out {duplicate_count} duplicate jobs")

        # Fetch detailed descriptions
        jobs_with_descriptions = await self.fetch_job_descriptions(jobs)

        # Save results
        await self.save_results(jobs_with_descriptions)
        self.print_sample(jobs_with_descriptions)

        return jobs_with_descriptions

    async def fetch_jobs_from_listing(self):
        """Fetch jobs from SuccessFactors listing page"""
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                print(f"Loading {self.company_name} careers page...")
                await self.random_delay(1, 2)
                await page.goto(self.jobs_url, wait_until='domcontentloaded', timeout=45000)

                await self.random_delay(4, 6)
                await self.simulate_human_behavior(page)

                # Wait for job list links matching SuccessFactors pattern
                try:
                    await page.wait_for_selector('a.jobTitle-link', timeout=20000)
                except Exception:
                    pass

                # Grab anything linking to a /job/ path as a fallback
                job_links = await page.evaluate('''() => {
                    let links = Array.from(document.querySelectorAll('a'));
                    return links.filter(a => a.href.includes('/job/') && a.innerText.trim().length > 3).map(a => ({
                        href: a.href,
                        title: a.innerText.trim()
                    }));
                }''')
                
                # Remove duplicates by href
                unique_links = {}
                for l in job_links:
                    if l['href'] not in unique_links:
                        unique_links[l['href']] = l['title']

                print(f"✓ Found {len(unique_links)} jobs")

                if not unique_links:
                    return jobs

                for href, title in list(unique_links.items())[:self.max_jobs] if self.max_jobs else unique_links.items():
                    try:
                        job_url = href if href.startswith('http') else f"{self.base_url}{href}"
                        
                        job_id = None
                        match = re.search(r'/(\d+)/?$', job_url)
                        if match:
                            job_id = match.group(1)
                        if not job_id:
                            job_id = f"aegean_{len(jobs) + 1}"

                        job_data = {
                            'job_id': f"aegean_{job_id}",
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
                print(f"❌ Error fetching jobs: {e}")
            finally:
                await context.close()
                await browser.close()
        return jobs

    async def fetch_job_descriptions(self, jobs):
        """Fetch detailed descriptions for each job"""
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
            await page.goto(job['url'], wait_until='load', timeout=30000)
            await self.random_delay(2, 4)
            await self.simulate_human_behavior(page)

            # SuccessFactors typically has .job-location or similar
            location_selectors = ['span.job-location', 'li.job-location', '.job-location', '[data-location]', '[itemprop="jobLocation"]']
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

            desc_selectors = ['#jobDescription', '.job-description', '[itemprop="description"]', '.content', 'article', 'main']
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

            # Extract posted date
            posted_date = await self.extract_posted_date_from_page(page)
            if posted_date:
                job['posted_date'] = posted_date

            job['description'] = description

            await page.close()
            await context.close()

        except Exception as e:
            print(f"  Error fetching description for {job['job_id']}: {e}")
