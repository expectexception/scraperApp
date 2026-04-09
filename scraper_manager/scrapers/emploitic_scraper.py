"""
Emploitic Careers Scraper
Extracts job listings from emploitic.com (Algeria)
"""

import asyncio
import re
from datetime import datetime
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict


class EmploiticScraper(BaseScraper):
    """Scraper for Emploitic Job Portal"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, 'emploitic', db_manager=db_manager)
        self.site_config = config.get('sites', {}).get('emploitic', {})
        self.base_url = self.site_config.get('base_url', 'https://emploitic.com')
        self.jobs_url = self.site_config.get('jobs_url', 'https://emploitic.com/offres-d-emploi')
        # Keywords to search specifically for aviation roles on this portal
        self.search_keywords = ["Aviation", "Aéronautique", "Dispatcher", "Operations"]

    async def run(self):
        """Main execution method"""
        self.print_header()

        all_jobs = []
        for keyword in self.search_keywords:
            self.logger.info(f"Searching Emploitic for keyword: '{keyword}'...")
            jobs_raw = await self.fetch_jobs_for_keyword(keyword)
            all_jobs.extend(jobs_raw)

        # Remove duplicates from the same run
        unique_jobs = []
        seen_urls = set()
        for job in all_jobs:
            if job['url'] not in seen_urls:
                unique_jobs.append(job)
                seen_urls.add(job['url'])

        jobs = [get_job_dict(**job) for job in unique_jobs]

        if not jobs:
            print("❌ No jobs found")
            return []

        print(f"\n✓ Extracted {len(jobs)} total jobs from gateway")

        # Apply title filtering BEFORE fetching descriptions
        if self.use_filter and self.filter_manager:
            print(f"\n🔍 Applying title filter...")
            matched_jobs, rejected_jobs, filter_stats = self.apply_title_filter(jobs)

            if not matched_jobs:
                print("❌ No jobs matched the filter criteria")
                return []

            print(f"✓ {len(matched_jobs)} jobs matched filter (will fetch descriptions)")
            print(f"✗ {len(rejected_jobs)} jobs rejected (not relevant)")
            jobs = matched_jobs

        # Filter duplicates against database
        jobs, duplicate_count = await self.filter_new_jobs(jobs)
        if duplicate_count > 0:
            print(f"\n🔄 Filtered out {duplicate_count} duplicate jobs")

        if not jobs:
            print("✓ All jobs are already in database or filtered out")
            return []

        # Fetch detailed descriptions
        jobs_with_descriptions = await self.fetch_job_descriptions(jobs)

        # Save results
        await self.save_results(jobs_with_descriptions)
        self.print_sample(jobs_with_descriptions)

        return jobs_with_descriptions

    async def fetch_jobs_for_keyword(self, keyword):
        """Fetch jobs for a specific keyword across multiple pages"""
        jobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                # Pagination loop
                for p_num in range(1, self.max_pages + 1):
                    search_url = f"{self.jobs_url}?search={keyword}&page={p_num}"
                    self.logger.info(f"Loading page {p_num}: {search_url}")
                    
                    await page.goto(search_url, wait_until='load', timeout=60000)
                    await self.random_delay(3, 5)
                    await self.simulate_human_behavior(page)

                    # Check for job list items
                    # Based on exploration: li elements in the listing
                    job_items = await page.query_selector_all('li[class*="job"], .job-item, li')
                    
                    found_on_page = 0
                    for item in job_items:
                        try:
                            # Verify if it's a real job item by looking for link and title
                            link_el = await item.query_selector('a[href*="/offres-d-emploi/"]')
                            if not link_el:
                                continue
                                
                            title_el = await item.query_selector('h2')
                            if not title_el:
                                continue
                                
                            title = (await title_el.inner_text()).strip()
                            href = await link_el.get_attribute('href')
                            
                            if not href or not title:
                                continue
                                
                            job_url = f"{self.base_url}{href}" if href.startswith('/') else href

                            # Company
                            company = "Unknown"
                            company_el = await item.query_selector('p, span[class*="company"]')
                            if company_el:
                                company = (await company_el.inner_text()).strip()

                            # Location
                            location = "Algeria"
                            loc_el = await item.query_selector('div[class*="location"], span[class*="location"]')
                            if loc_el:
                                location = (await loc_el.inner_text()).strip()

                            # Extract ID from URL
                            # Pattern: emploitic.com/.../offres-d-emploi/.../{id}
                            job_id_match = re.search(r'/([^/]+)$', href)
                            job_id_str = job_id_match.group(1) if job_id_match else f"emp_{len(jobs) + 1}"

                            job_data = {
                                'job_id': f"emploitic_{job_id_str}",
                                'title': title,
                                'company': company,
                                'source': self.site_key,
                                'url': job_url,
                                'apply_url': job_url,
                                'location': self.normalize_location(location),
                                'timestamp': datetime.now().isoformat(),
                                'description': '',
                            }
                            jobs.append(job_data)
                            found_on_page += 1

                            if self.max_jobs and len(jobs) >= self.max_jobs:
                                break
                        except Exception:
                            continue

                    self.logger.info(f"✓ Found {found_on_page} jobs for '{keyword}' on page {p_num}")
                    
                    if found_on_page == 0 or (self.max_jobs and len(jobs) >= self.max_jobs):
                        break

            except Exception as e:
                self.logger.error(f"Error fetching jobs for {keyword}: {e}")
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

        # Count jobs with descriptions
        with_desc = sum(1 for job in jobs if job.get('description'))
        print(f"✓ Successfully extracted {with_desc}/{len(jobs)} descriptions")

        return jobs

    async def _extract_description(self, browser, job):
        """Extract detailed description from Emploitic job page"""
        try:
            page, context = await self.setup_stealth_page(browser)

            # Load job detail page
            await page.goto(job['url'], wait_until='load', timeout=45000)
            await self.random_delay(2, 4)

            # Common selectors for Emploitic description
            desc_selectors = [
                'div[class*="description"]',
                '.job-body',
                '#job-details',
                '.description-content',
                '.content',
                'main',
            ]

            description = ''
            for selector in desc_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        text = await elem.inner_text()
                        if text and len(text) > 300:
                            description = text.strip()
                            break
                except Exception:
                    continue

            if not description:
                description = await self.extract_description_from_page(page)

            job['description'] = description

            await page.close()
            await context.close()

        except Exception:
            pass
