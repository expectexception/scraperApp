"""
PeopleClick / Cargolux Careers Scraper
Extracts aviation jobs from careers.peopleclick.eu.com (Cargolux client)

Notes:
- Uses robust selectors to find job links in the search results
- Extracts job_id, title, company, url, location, posted_date
- Fetches job detail pages to extract description and other metadata
"""

from playwright.async_api import async_playwright, TimeoutError
import asyncio
import re
from datetime import datetime
from typing import List, Dict
from .base_scraper import BaseScraper
from .job_schema import get_job_dict


class CargoluxPeopleClickScraper(BaseScraper):
    """Scraper for Cargolux Careers (PeopleClick)
    """

    def __init__(self, config: dict, db_manager=None):
        super().__init__(config, 'cargolux', db_manager=db_manager)
        self.site_config = config.get('sites', {}).get('cargolux', {})
        self.base_url = self.site_config.get('base_url', 'https://careers.peopleclick.eu.com')
        self.jobs_url = self.site_config.get('jobs_url', 'https://careers.peopleclick.eu.com/careerscp/client_cargolux/external/results/searchResult.html')

    async def run(self):
        """Main execution method"""
        self.print_header()

        print(f"Fetching jobs from {self.site_config.get('name')}...")
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

            print(f"✓ {len(matched_jobs)} jobs matched filter (will fetch descriptions)")
            print(f"✗ {len(rejected_jobs)} jobs rejected (not relevant)")
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

    async def fetch_jobs_from_listing(self) -> List[Dict]:
        """Fetch jobs from PeopleClick listing page"""
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                print("Loading PeopleClick/Cargolux listing page...")
                await self.random_delay(1, 2)
                try:
                    resp, html, blocked = await self.safe_page_goto(page, self.jobs_url, timeout=30000)
                    if blocked:
                        print("PeopleClick listing page is blocked; aborting this search")
                        return []
                    if resp is None:
                        print("Could not fetch job listing page (robots or network); skipping")
                        return []
                except Exception:
                    # Fallback to direct goto if safe wrapper not available - add retry attempts
                    success = False
                    for attempt in range(1, 4):
                        try:
                            await page.goto(self.jobs_url, wait_until='domcontentloaded', timeout=30000 * attempt)
                            success = True
                            break
                        except Exception:
                            await asyncio.sleep(1 * attempt)
                    if not success:
                        # Re-raise so outer handler will log and continue
                        raise
                await self.random_delay(2, 4)
                await self.simulate_human_behavior(page)
                print("✓ Page loaded")

                # Try a set of selectors that commonly match PeopleClick listing links
                selectors = [
                    'a[href*="/careerscp/client_cargolux/external/en/job/"]',
                    'a[href*="/careerscp/client_cargolux/external/en/apply/"]',
                    'a[href*="/external/en/job/"]',
                    'a[href*="/job/"]',
                    'table.searchResult a',
                    'tr.jobRow a',
                ]

                job_links = []
                for sel in selectors:
                    try:
                        found = await page.query_selector_all(sel)
                        if found and len(found) > 0:
                            job_links.extend(found)
                    except Exception:
                        continue

                if job_links:
                    print(f"Found {len(job_links)} candidate anchors using common selectors")

                # If no links were found using common selectors, try navigating to the search page and submitting an empty search
                if not job_links:
                    try:
                        # Try to find a dedicated search link on the page
                        search_link = await page.query_selector('a:has-text("Search")')
                        if not search_link:
                            search_link = await page.query_selector('a:has-text("Advanced")')
                        if search_link:
                            print("Found Search/Advanced link; navigating to search page to trigger results")
                            try:
                                await search_link.click()
                                await page.wait_for_load_state('domcontentloaded')
                                await self.random_delay(1, 2)
                            except Exception:
                                pass
                        else:
                            # Try to construct direct path to search page and include locale param to ensure results
                            search_page = f"{self.base_url}/careerscp/client_cargolux/external/search/search.html?localeCode=en-us"
                            await page.goto(search_page, wait_until='domcontentloaded', timeout=20000)
                            await self.random_delay(1, 2)

                        # Try to click the search button to list all jobs
                        print("Trying to click search button...")
                        try:
                            # Try multiple selectors for the search button
                            search_btn_selectors = [
                                '#sp-searchButton',
                                'input#sp-searchButton',
                                'button#sp-searchButton',
                                'input[value="Search"]',
                                'button:has-text("Search")',
                                'a.pf-rwd-searchButton' # Potential class
                            ]
                            
                            clicked = False
                            for btn_sel in search_btn_selectors:
                                try:
                                    if await page.is_visible(btn_sel):
                                        print(f"Clicking search button: {btn_sel}")
                                        await page.click(btn_sel)
                                        clicked = True
                                        break
                                except Exception:
                                    continue
                            
                            if clicked:
                                print("Search button clicked, waiting for results...")
                                await self.random_delay(2, 4)
                                # Wait for results to appear
                                try:
                                    await page.wait_for_selector('a[href*="/job/"]', timeout=10000)
                                    print("Results loaded")
                                except Exception:
                                    print("Timeout waiting for results after click")
                        except Exception as e:
                            print(f"Error acting on search button: {e}")
                    except Exception:
                        pass

                # If no links were found using common selectors, scan ALL anchors and onclicks as fallback
                if not job_links:
                    all_anchors = await page.query_selector_all('a')
                    print(f"Found {len(all_anchors)} total anchors; scanning for candidate job links...")
                    for a in all_anchors:
                        try:
                            href = await a.get_attribute('href')
                            if href and ('/job' in href or 'jobId=' in href or '/external/en/job/' in href):
                                job_links.append(a)
                                continue
                            # Check for onclick-based job links (javascript invocation)
                            onclick = await a.get_attribute('onclick')
                            if onclick and ('jobId' in onclick or 'openJob' in onclick or 'showJob' in onclick.lower()):
                                job_links.append(a)
                                continue
                        except Exception:
                            continue
                    # If still nothing, log sample anchors for debugging to help tune selectors
                    sample_anchors = []
                    for a in all_anchors[:20]:
                        try:
                            href = await a.get_attribute('href')
                            onclick = await a.get_attribute('onclick')
                            txt = (await a.inner_text()).strip()
                            sample_anchors.append({'href': href, 'onclick': onclick, 'text': txt[:80]})
                        except Exception:
                            continue
                    if not job_links:
                        print(f"No candidate job anchors found using heuristics. Sample anchors (first 20):")
                        for s in sample_anchors:
                            print(f"  href={s['href']}, onclick={s['onclick']}, text={s['text']}")
                # Deduplicate link elements using href
                seen = set()
                for link in job_links:
                    try:
                        href = await link.get_attribute('href')
                        if not href:
                            # If href is missing, try to use onclick raw attribute to construct a URL
                            onclick = await link.get_attribute('onclick')
                            href = onclick if onclick else None
                            if not href:
                                continue
                        if href in seen:
                            continue
                        seen.add(href)

                        # Resolve relative hrefs correctly using the current page URL
                        from urllib.parse import urljoin, urlparse, parse_qs
                        try:
                            job_url = urljoin(page.url, href)
                        except Exception:
                            if href.startswith('/'):
                                job_url = f"{self.base_url}{href}"
                            elif href.startswith('http'):
                                job_url = href
                            else:
                                job_url = f"{self.base_url}/{href}"

                        # Extract title (link text)
                        title = (await link.inner_text()).strip()
                        # Sanity checks
                        if not title or len(title) < 3:
                            continue

                        # Derive job_id from href pattern (last path element) or jobId parameter
                        job_id = None
                        m = re.search(r'jobPostId=(\d+)', job_url)
                        if not m:
                            m = re.search(r'jobId=(\d+)', job_url)
                        if m:
                            job_id = m.group(1)
                        else:
                            # Fallback: last path segment if looks like an ID or slug
                            parts = href.split('/') if href else []
                            if parts:
                                last = parts[-1]
                                if last and len(last) > 0:
                                    job_id = last
                        if not job_id:
                            job_id = f"peopleclick_{len(jobs)+1}"
                        job_data = {
                            'job_id': f"peopleclick_{job_id}",
                            'title': title,
                            'company': self.site_config.get('name', 'Cargolux'),
                            'source': 'cargolux',
                            'url': job_url,
                            'apply_url': job_url,
                            'location': '',
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
                        print(f"  -> Candidate job: {job_data['title']} ({job_data['url']})")

                        if self.max_jobs and len(jobs) >= self.max_jobs:
                            break

                    except Exception:
                        continue

            except Exception as e:
                print(f"❌ Error fetching PeopleClick jobs: {e}")
            finally:
                await context.close()
                await browser.close()

        return jobs

    async def fetch_job_descriptions(self, jobs: List[Dict]) -> List[Dict]:
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

    async def _extract_description(self, browser, job: dict):
        """Extract detailed description and metadata from job page"""
        try:
            page, context = await self.setup_stealth_page(browser)
            await self.random_delay(1, 2)
            await page.goto(job['url'], wait_until='domcontentloaded', timeout=30000)
            await self.random_delay(2, 4)
            await self.simulate_human_behavior(page)

            # Update title from page if available
            page_title = await page.title()
            if page_title and len(page_title) > 3:
                # Sometimes page title includes company or site name
                job['title'] = page_title.strip()

            # Extract body text and search for common labels
            body_text = await page.inner_text('body')

            # Location
            loc_match = re.search(r'Location[:\s]+([^\n\r•]+)', body_text, re.IGNORECASE)
            if loc_match:
                job['location'] = loc_match.group(1).strip()

            # Posted date (formatted as 'Posted Date: DD/MM/YYYY' or similar)
            date_match = re.search(r'(Posted Date|Date Posted|Published)[:\s]+([^\n\r•]+)', body_text, re.IGNORECASE)
            if date_match:
                date_text = date_match.group(2).strip()
                parsed = self.parse_posted_date(date_text)
                job['posted_date'] = parsed if parsed else date_text

            # Fallback: try page-level heuristics if posted_date still missing
            if not job.get('posted_date'):
                try:
                    fallback_pd = await self.extract_posted_date_from_page(page)
                    if fallback_pd:
                        job['posted_date'] = fallback_pd
                except Exception:
                    pass

            # Extract description
            # Find common description containers
            desc_selectors = ['#jobDescription', '.jobAdBody', '.jobDescription', '.description', '.job-description', 'div[class*="jobDetail"]', 'div[id*="jobDetail"]', '.jobFullDescription', '#divJobDescription', 'article', 'main']
            description_parts = []
            for sel in desc_selectors:
                try:
                    elem = await page.query_selector(sel)
                    if elem:
                        txt = await elem.inner_text()
                        if txt and len(txt) > 100:
                            description_parts.append(txt.strip())
                            break
                except Exception:
                    continue

            # Fallback: try to extract large bodies
            if not description_parts:
                body_text = await page.inner_text('body')
                if len(body_text) > 300:
                    description_parts.append(body_text[:4000])

            if description_parts:
                # Some pages include header nav text; try to extract the portion starting from 'JOB DETAILS' or the first header occurrence
                desc = '\n\n'.join(description_parts)
                idx = desc.find('JOB DETAILS')
                if idx > 0:
                    desc = desc[idx:]
                job['description'] = desc
            else:
                # Try fallback page-level description extraction
                try:
                    fallback_desc = await self.extract_description_from_page(page)
                    if fallback_desc:
                        job['description'] = fallback_desc
                except Exception:
                    pass

            await page.close()
            await context.close()

        except TimeoutError:
            print(f"  Timeout for {job['job_id']}")
        except Exception as e:
            print(f"  Error fetching description for {job.get('job_id', job.get('url'))}: {e}")
