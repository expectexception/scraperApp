"""
Dubai Royal Air Wing Scraper
Extracts aviation job listings from dubairaw.com (Often unlisted/private)
"""

import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
import logging

logger = logging.getLogger(__name__)

class DubaiRawScraper(BaseScraper):
    """Scraper for Dubai Royal Air Wing Careers"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, 'dubairaw', db_manager=db_manager)
        self.site_config = config.get('sites', {}).get('dubairaw', {})
        self.base_url = self.site_config.get('base_url', 'https://careers.dubaiairports.ae')
        self.jobs_url = self.site_config.get('jobs_url', 'https://careers.dubaiairports.ae/search-jobs')

    async def run(self):
        """Main execution method"""
        self.print_header()

        logger.info(f"Fetching jobs from {self.company_name}...")
        logger.info(f"URL: {self.jobs_url}")
        logger.info("NOTE: Dubai Royal Air Wing typically recruits privately and jobs are rarely listed.")

        jobs = await self.fetch_jobs_from_listing()
        
        if not jobs:
            logger.warning("No jobs found (Expected for Dubai Royal Air Wing)")
            return []

        logger.info(f"Extracted {len(jobs)} jobs from listing")

        # Apply title filtering BEFORE fetching descriptions
        if self.use_filter and self.filter_manager:
            logger.info("Applying title filter...")
            matched_jobs, rejected_jobs, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

            if not matched_jobs:
                logger.warning("No jobs matched the filter criteria")
                return []
            jobs = matched_jobs

        # Filter duplicates
        jobs, duplicate_count = await self.filter_new_jobs(jobs)
        if duplicate_count > 0:
            logger.info(f"Filtered out {duplicate_count} duplicate jobs")

        # Fetch detailed descriptions
        jobs_with_descriptions = await self.fetch_job_descriptions(jobs)

        # Save results
        await self.save_results(jobs_with_descriptions)
        self.print_sample(jobs_with_descriptions)

        return jobs_with_descriptions

    async def fetch_jobs_from_listing(self):
        """Fetch jobs from Dubai RAW site if they exist"""
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless, args=['--disable-blink-features=AutomationControlled'])
            page, context = await self.setup_stealth_page(browser)

            try:
                # Due to the private nature, this will likely timeout or fail for a strict job board.
                # However, we'll try a generic parsing technique across standard links.
                logger.info("Loading Dubai Royal Air Wing page...")
                await self.random_delay(2, 4)
                await page.goto(self.jobs_url, wait_until='domcontentloaded', timeout=30000)

                # Wait for dynamic content to load
                await self.random_delay(3, 5)
                await self.simulate_human_behavior(page)

                # generic link check
                anchors = await page.query_selector_all('a')
                job_links = []
                for a in anchors:
                    href = await a.get_attribute('href')
                    if href and any(k in href.lower() for k in ['/job', '/career', 'vacancy', 'opening']):
                        txt = await a.inner_text()
                        if txt and len(txt.strip()) > 3:
                            job_links.append(a)

                # Extract job data from links
                added_urls = set()
                for link in job_links:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    try:
                        href = await link.get_attribute('href')
                        if not href:
                            continue

                        # Build full URL
                        if href.startswith('/'):
                            job_url = f"{self.base_url}{href}"
                        elif href.startswith('http'):
                            job_url = href
                        else:
                            job_url = f"{self.base_url}/{href}"

                        if job_url in added_urls:
                            continue

                        # Extract title from link text
                        title = (await link.inner_text()).strip()
                        if not title or len(title) < 4:
                            continue

                        job_id = f"dubairaw_{len(jobs) + 1}_{datetime.now().strftime('%Y%m%d')}"

                        job_data = {
                            'job_id': job_id,
                            'title': title,
                            'company': 'Dubai Royal Air Wing',
                            'source': 'dubairaw',
                            'url': job_url,
                            'apply_url': job_url,
                            'location': 'Dubai, UAE',
                            'job_type': '',
                            'department': '',
                            'posted_date': '',
                            'closing_date': '',
                            'timestamp': datetime.now().isoformat(),
                            'description': '',
                            'requirements': '',
                            'qualifications': '',
                        }

                        jobs.append(job_data)
                        added_urls.add(job_url)

                    except Exception as e:
                        continue

            except asyncio.TimeoutError:
                logger.error("Timeout loading page - site might be restricted or down.")
            except Exception as e:
                logger.error(f"Error fetching jobs: {e}")
            finally:
                await context.close()
                await browser.close()

        return jobs

    async def fetch_job_descriptions(self, jobs):
        """Fetch detailed descriptions for each job"""
        if not jobs:
             return jobs

        logger.info(f"Fetching detailed descriptions for {len(jobs)} jobs...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless, args=['--disable-blink-features=AutomationControlled'])

            for i in range(0, len(jobs), self.batch_size):
                batch = jobs[i:i + self.batch_size]
                tasks = []

                for job in batch:
                    if job.get('url'):
                        tasks.append(self._extract_description(browser, job))

                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

                logger.info(f"  Processed {min(i + self.batch_size, len(jobs))}/{len(jobs)} jobs")
                await asyncio.sleep(1) # Extra cooling delay

            await browser.close()

        return jobs

    async def _extract_description(self, browser, job):
        """Extract detailed description from job page"""
        try:
            page, context = await self.setup_stealth_page(browser)

            # Load job detail page
            await self.random_delay(1, 3)
            await page.goto(job['url'], wait_until='load', timeout=30000)
            await self.random_delay(2, 4)
            await self.simulate_human_behavior(page)

            # Generic fallback
            description = ''
            try:
                fallback_desc = await self.extract_description_from_page(page)
                if fallback_desc and len(fallback_desc) > 100:
                    description = fallback_desc
            except Exception:
                pass

            job['description'] = description

            # Date fallback
            if not job.get('posted_date'):
               date = await self.extract_posted_date_from_page(page)
               if date:
                   job['posted_date'] = date

            await page.close()
            await context.close()

        except asyncio.TimeoutError:
            logger.warning(f"Timeout for {job['job_id']}")
        except Exception as e:
            logger.error(f"Error fetching description for {job['job_id']}: {e}")
