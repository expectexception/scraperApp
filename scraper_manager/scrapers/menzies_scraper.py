"""
Menzies Aviation Careers Scraper
Extracts aviation job listings from careers.jmenzies.com (Oleeo Platform)
"""

import asyncio
import re
from datetime import datetime
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict


class MenziesScraper(BaseScraper):
    """Scraper for Menzies Aviation Careers"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, 'menzies', db_manager=db_manager)
        self.site_config = config.get('sites', {}).get('menzies', {})
        self.base_url = self.site_config.get('base_url', 'https://careers.jmenzies.com')
        self.jobs_url = self.site_config.get('jobs_url', 'https://careers.jmenzies.com/aviation/vacancy/find/results/')

    async def run(self):
        """Main execution method"""
        self.print_header()

        print(f"Fetching jobs from {self.company_name}...")
        
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

            if not matched_jobs:
                print("❌ No jobs matched the filter criteria")
                return []

            print(f"✓ {len(matched_jobs)} jobs matched filter (will fetch descriptions)")
            print(f"✗ {len(rejected_jobs)} jobs rejected (not relevant)")
            jobs = matched_jobs

        # Filter duplicates
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

    async def fetch_jobs_from_listing(self):
        """Fetch job listings handled by AJAX/Oleeo"""
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                print(f"Navigating to {self.jobs_url}")
                await page.goto(self.jobs_url, wait_until='load', timeout=60000)
                await self.random_delay(3, 5)
                
                # Handle potential cookie banner
                try:
                    cookie_btn = await page.query_selector('button:has-text("Accept"), .cookie-accept, #accept-cookies')
                    if cookie_btn: await cookie_btn.click()
                except Exception: pass

                for p_num in range(1, self.max_pages + 1):
                    print(f"Processing page {p_num}...")
                    
                    # Wait for results to stabilize
                    await page.wait_for_selector('a.rcMenu', timeout=30000)
                    await self.random_delay(2, 3)
                    
                    # Extract jobs from current page
                    elements = await page.query_selector_all('a.rcMenu')
                    
                    for el in elements:
                        try:
                            title = (await el.inner_text()).strip()
                            href = await el.get_attribute('href')
                            if not href or '/vacancy/' not in href: continue
                            
                            job_url = f"{self.base_url}{href}" if href.startswith('/') else href
                            
                            # Attempt to get location from parent/sibling
                            # Oleeo often has metadata in the same cell or near the link
                            location = "Unknown"
                            parent = await el.evaluate_handle('el => el.closest("td") or el.parentElement')
                            if parent:
                               # Check for location in siblings or parent text
                               loc_el = await page.evaluate('(parent) => { let text = parent.innerText || ""; return text.split("\\n").find(t => t.includes(",") || t.length > 5 && !t.includes("Closing Date")) || "Global"; }', parent)
                               if loc_el: location = loc_el.strip()

                            # Extract ID from URL
                            job_id_match = re.search(r'/(\d+)/?$', href)
                            job_id = job_id_match.group(1) if job_id_match else f"menz_{len(jobs)+1}"

                            job_data = {
                                'job_id': f"menzies_{job_id}",
                                'title': title,
                                'company': self.company_name,
                                'source': self.site_key,
                                'url': job_url,
                                'apply_url': job_url,
                                'location': self.normalize_location(location),
                                'timestamp': datetime.now().isoformat(),
                                'description': '',
                            }
                            jobs.append(job_data)

                            if self.max_jobs and len(jobs) >= self.max_jobs:
                                break
                        except Exception:
                            continue

                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    # Pagination: click 'Next'
                    next_btn = await page.query_selector('a.scroller_movenext.buttonEnabled')
                    if next_btn:
                        print("Clicking 'Next' page...")
                        await next_btn.click()
                        await asyncio.sleep(3) # Wait for AJAX
                    else:
                        print("No more pages available.")
                        break

            except Exception as e:
                print(f"❌ Error fetching Menzies listings: {e}")
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
        """Extract detailed description from Menzies job page"""
        try:
            page, context = await self.setup_stealth_page(browser)

            # Load job detail page
            await page.goto(job['url'], wait_until='load', timeout=45000)
            await self.random_delay(2, 4)

            # Oleeo detail pages often use id="maincontent" or specific divs
            desc_selectors = [
                '#maincontent',
                '.job-description',
                '.vacancy-details',
                '.rcMenu',
                'main',
                '#content',
            ]

            description = ''
            for selector in desc_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        text = await elem.inner_text()
                        if text and len(text) > 400:
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
