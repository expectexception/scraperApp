"""
LinkedIn Jobs Scraper
Extracts aviation jobs from LinkedIn job search
"""

from playwright.async_api import async_playwright, TimeoutError
import asyncio
import time
import random
import logging
import re
import signal
import sys
from datetime import datetime, timedelta
from typing import List, Dict
from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    """Scraper for LinkedIn job postings"""

    def __init__(self, config: dict, db_manager=None):
        super().__init__(config, 'linkedin', db_manager=db_manager)
        self.search_url = "https://www.linkedin.com/jobs/search/"
        
        # Support both single values and lists
        self.default_posts = self.site_config.get('default_post', ['aviation'])
        if isinstance(self.default_posts, str):
            self.default_posts = [self.default_posts]
            
        self.default_locations = self.site_config.get('default_location', ['Worldwide'])
        if isinstance(self.default_locations, str):
            self.default_locations = [self.default_locations]
        
        # Track collected jobs for graceful shutdown
        self.collected_jobs = []
        self.shutdown_requested = False

    async def dismiss_cookie_banner(self, page):
        """Try to dismiss the cookie banner if it appears"""
        try:
            await page.get_by_role("button", name="Dismiss").click(timeout=5000)
            print("Dismissed cookie banner.")
        except TimeoutError:
            print("No 'Dismiss' button found, continuing...")

    async def random_scroll_page(self, page):
        """Simulate human-like scrolling (renamed to avoid attribute name clash)"""
        scroll_amount = random.randint(200, 600)
        await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        await asyncio.sleep(random.uniform(0.5, 1.5))



    async def random_mouse_move(self, page):
        """Simulate random mouse movements"""
        x = random.randint(100, 800)
        y = random.randint(100, 600)
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.2, 0.8))

    async def scrape_linkedin_jobs(self, page, post_name: str, location_name: str, max_jobs: int) -> List[Dict]:
        """Scrape LinkedIn jobs for given search parameters using existing page"""
        all_jobs_data = []
        failed_card_indices = set()  # Track cards that failed in current search

        # Initial search
        try:
            # Build search URL directly instead of filling form
            import urllib.parse
            keywords = urllib.parse.quote(post_name)
            location = urllib.parse.quote(location_name)
            search_url_with_params = f"{self.search_url}?keywords={keywords}&location={location}"
            
            # Navigate to search results
            await page.goto(search_url_with_params, timeout=30000)
            await self.random_delay(5, 8)

            # Try to dismiss the cookie banner if it appears
            await self.dismiss_cookie_banner(page)

            await self.random_delay(3, 5)
            await self.random_scroll_page(page)
            await self.random_mouse_move(page)

            await self.random_delay(3, 5)

            # Waiting for results list
            try:
                await page.wait_for_selector("ul.jobs-search__results-list", timeout=30000)
                print("Job list found.")
                await self.random_scroll_page(page)
            except TimeoutError:
                print("Could not find job list. Page might have changed.")
                return []
        except Exception as e:
            print(f"Error during initial search setup: {e}")
            return []

        # Get all the job cards from the left panel
        job_cards = await page.locator("ul.jobs-search__results-list div.base-search-card").all()

        print(f"Found {len(job_cards)} job cards on the page.")
        
        # If no job cards found, skip this search and move to next
        if not job_cards or len(job_cards) == 0:
            print(f"⚠️ No job cards found for '{post_name}' in '{location_name}'. Skipping to next search...")
            return []
        
        print(f"Scraping ALL job cards and applying title filtering...")

        count = 0

        # Loop through each job card - scrape all available
        for i in range(len(job_cards)):
            # Skip cards that failed in previous search
            if i in failed_card_indices:
                print(f"⊘ Skipping job card {i+1} (failed in previous search - marked to retry)")
                continue

            # Refetch job cards fresh each time to avoid stale references
            current_job_cards = await page.locator("ul.jobs-search__results-list div.base-search-card").all()
            
            if not current_job_cards or len(current_job_cards) == 0:
                print(f"⚠️ Job cards no longer available. All cards processed. Moving to next search...")
                break
            
            if i >= len(current_job_cards):
                print(f"Job card {i+1} no longer available. Stopping iteration.")
                break
                
            job_card = current_job_cards[i]

            await self.random_delay(6, 10)
            
            # Dismiss any cookie banner that might appear
            try:
                await self.dismiss_cookie_banner(page)
            except Exception:
                pass

            job_data = {}

            # Scrape basic info from the list card with retry on timeout
            title = None
            company = None
            location = None
            link = None
                
            try:
                # Use longer timeout for card extraction (5 seconds) for better page loading
                title = await job_card.locator("h3.base-search-card__title").inner_text(timeout=5000)
                title = title.strip()

                company = await job_card.locator("h4.base-search-card__subtitle").inner_text(timeout=5000)
                company = company.strip()

                location = await job_card.locator("span.job-search-card__location").inner_text(timeout=5000)
                location = location.strip()

                link_element = job_card.locator("a.base-card__full-link")
                link = await link_element.get_attribute("href")

                # Link correction logic
                if link and not link.startswith("http"):
                    link = f"https://www.linkedin.com{link}"
            except TimeoutError:
                print(f"\n❌ Timeout extracting job {i+1}. Re-searching and continuing with other cards...")
                failed_card_indices.add(i)
                
                # Re-search for the same Position + Location
                print(f"🔄 Re-searching for '{post_name}' in '{location_name}'...")
                try:
                    import urllib.parse
                    keywords = urllib.parse.quote(post_name)
                    location = urllib.parse.quote(location_name)
                    search_url_with_params = f"{self.search_url}?keywords={keywords}&location={location}"
                    await page.goto(search_url_with_params, timeout=30000)
                    await self.random_delay(4, 6)
                    await self.dismiss_cookie_banner(page)
                    await self.random_delay(2, 3)
                    await page.wait_for_selector("ul.jobs-search__results-list", timeout=30000)
                    print("✅ Re-search complete. Continuing with other job cards...")
                except Exception as e:
                    print(f"❌ Re-search failed: {e}")
                
                continue
                    
            except Exception as e:
                print(f"\n❌ Error scraping basic info for job {i+1}: {e}. Re-searching and continuing...")
                failed_card_indices.add(i)
                
                # Re-search for the same Position + Location
                print(f"🔄 Re-searching for '{post_name}' in '{location_name}'...")
                try:
                    import urllib.parse
                    keywords = urllib.parse.quote(post_name)
                    location = urllib.parse.quote(location_name)
                    search_url_with_params = f"{self.search_url}?keywords={keywords}&location={location}"
                    await page.goto(search_url_with_params, timeout=30000)
                    await self.random_delay(4, 6)
                    await self.dismiss_cookie_banner(page)
                    await self.random_delay(2, 3)
                    await page.wait_for_selector("ul.jobs-search__results-list", timeout=30000)
                    print("✅ Re-search complete. Continuing with other job cards...")
                except Exception as e2:
                    print(f"❌ Re-search failed: {e2}")
                
                continue

            # Only proceed if we successfully extracted basic info
            if not title or not company or not link:
                print(f"Skipping job {i+1} - missing required info")
                continue

            job_data['title'] = title
            job_data['company'] = company
            job_data['location'] = location
            job_data['url'] = link
            job_data['apply_url'] = link
            job_data['source'] = self.site_key
            job_data['job_id'] = f"linkedin_{post_name.replace(' ', '_')}_{location_name.replace(' ', '_')}_{i+1}"
            job_data['timestamp'] = datetime.now().isoformat()

            print(f"\nScraping job {i+1}: {title} at {company}")

            # Click the card and scrape the details pane
            try:
                # Scroll to the job card and simulate human interaction
                await job_card.scroll_into_view_if_needed()
                await self.random_delay(2, 3)
                await self.random_mouse_move(page)

                # Click the card to load the details on the right
                await job_card.click()
                await self.random_delay(4, 6)
                
                # Dismiss any cookie banner that might appear after clicking
                try:
                    await self.dismiss_cookie_banner(page)
                except Exception:
                    pass
                
                await self.random_scroll_page(page)

                # Wait for the details pane to update with longer timeout
                await page.wait_for_selector("div.description__text", timeout=8000)
                
                # Dismiss cookie banner if it appears while waiting for details
                try:
                    await self.dismiss_cookie_banner(page)
                except Exception:
                    pass

                # Try to expand the full description
                try:
                    show_more_button = page.locator("button:has-text('See more')").first
                    if not await show_more_button.is_visible():
                        show_more_button = page.locator("button:has-text('Show more')").first
                    if await show_more_button.is_visible():
                        await show_more_button.click()
                        await self.random_delay(2, 3)
                        
                        # Dismiss cookie banner if it appears during expansion
                        try:
                            await self.dismiss_cookie_banner(page)
                        except Exception:
                            pass
                        
                        print("Expanded full description")
                        await self.random_scroll_page(page)
                        await self.random_delay(2, 3)
                except Exception as e:
                    print(f"No 'See more'/'Show more' button or error: {e}")

                # Scrape the description and posted time
                description_element = page.locator("div.description__text")
                description = await description_element.inner_text()
                description = description.strip()

                # Posted time — make extraction robust and normalize
                posted = None
                try:
                    posted_element = page.locator('span.posted-time-ago__text')
                    posted_text = await posted_element.inner_text()
                    posted = posted_text.strip() if posted_text else None
                except Exception:
                    # Attempt to read from list-card area as fallback
                    try:
                        posted_text = await job_card.locator("time").inner_text()
                        posted = posted_text.strip() if posted_text else None
                    except Exception:
                        posted = None

                # Use base class date parser
                normalized_posted = self.parse_posted_date(posted) if posted else None

                job_data['description'] = description
                job_data['posted_date'] = normalized_posted
                # Fallback: if posted_date not found, check page for meta/json-ld/relative text
                if not job_data.get('posted_date'):
                    try:
                        fallback_pd = await self.extract_posted_date_from_page(page)
                        if fallback_pd:
                            job_data['posted_date'] = fallback_pd
                    except Exception:
                        pass
                # Fallback: if description too short, try base heuristic
                if not job_data.get('description') or len(job_data.get('description') or '') < 80:
                    try:
                        fallback_desc = await self.extract_description_from_page(page)
                        if fallback_desc and len(fallback_desc) > len(job_data.get('description') or ''):
                            job_data['description'] = fallback_desc
                    except Exception:
                        pass
                print(f'Posted: {posted} -> {normalized_posted}')

                # Scrape the job criteria
                criteria = {}
                criteria_items = await page.locator("li.description__job-criteria-item").all()
                for item in criteria_items:
                    try:
                        subheader_element = item.locator("h3.description__job-criteria-subheader")
                        subheader = await subheader_element.inner_text()
                        subheader = subheader.strip()

                        text_element = item.locator("span.description__job-criteria-text")
                        text = await text_element.inner_text()
                        text = text.strip()

                        criteria[subheader] = text
                    except Exception:
                        continue

                job_data['criteria'] = criteria

                # Scrape additional details
                additional_details = {}
                try:
                    insight_items = await page.locator("div.job-details-jobs-unified-top-card__job-insight").all()
                    for item in insight_items:
                        try:
                            text = await item.inner_text()
                            text = text.strip()

                            if "salary" in text.lower() or "$" in text:
                                salary_info = self.parse_salary(text)
                                additional_details.update(salary_info)
                                additional_details['salary_raw'] = text
                            elif "benefits" in text.lower():
                                additional_details['benefits'] = text
                            else:
                                if 'other_insights' not in additional_details:
                                    additional_details['other_insights'] = []
                                additional_details['other_insights'].append(text)
                        except Exception:
                            continue
                except Exception as e:
                    print(f"Error scraping additional details: {e}")

                job_data['additional_details'] = additional_details
                # Map salary fields to job_data for get_job_dict
                job_data['salary_min'] = additional_details.get('salary_min')
                job_data['salary_max'] = additional_details.get('salary_max')
                job_data['salary_currency'] = additional_details.get('salary_currency', 'USD')

                print(f"Successfully scraped details for: {title}")

            except Exception as e:
                print(f"Could not load or scrape details for '{title}'. Error: {e}")
                print(f"   Scrolling back to job card list...")
                # Scroll back to the job list
                await page.evaluate("window.scrollBy(0, -800)")
                await self.random_delay(3, 4)
                job_data['description'] = ""
                job_data['criteria'] = {}
                job_data['additional_details'] = {}

            # After processing the job (success or failure), go back to job list if we're still on details page
            try:
                # Check if we're on a job details page by looking for the description element
                if await page.locator("div.description__text").count() > 0:
                    print(f"   Going back to job card list...")
                    await page.evaluate("window.scrollBy(0, -1000)")
                    await self.random_delay(2, 3)
            except Exception:
                pass

            # Ensure posted_date key exists
            job_data.setdefault('posted_date', None)

            # Convert to canonical job dict before appending so all scrapers produce same structure
            try:
                job_record = get_job_dict(**job_data)
            except Exception:
                # If canonicalization fails for unexpected keys, fall back to raw dict but keep key names consistent
                job_record = job_data

            # Add this job's data to our main list
            all_jobs_data.append(job_record)

            # Update the count
            count += 1
            print(f"--> Job {count} scraped and added to results")

            # Delay between jobs to avoid rate limiting
            await self.random_delay(5, 10)

        return all_jobs_data

    async def run(self):
        """Main execution method"""
        self.print_header()

        # Get search parameters from config or use defaults
        posts = self.site_config.get('search_post', self.site_config.get('default_post', self.default_posts))
        if isinstance(posts, str):
            posts = [posts]
            
        locations = self.site_config.get('search_location', self.site_config.get('default_location', self.default_locations))
        if isinstance(locations, str):
            locations = [locations]
            
        # When max_jobs is set, use it as the total limit, not per search
        if self.max_jobs:
            max_jobs_total = self.max_jobs
            # Distribute across searches, minimum 1 per search
            max_jobs_per_search = max(1, self.max_jobs // (len(posts) * len(locations)))
        else:
            max_jobs_per_search = 20
            max_jobs_total = self.site_config.get('max_jobs_total', max_jobs_per_search * len(posts) * len(locations))

        print(f"Searching for {len(posts)} job terms in {len(locations)} locations")
        print(f"Job terms: {', '.join(posts)}")
        print(f"Locations: {', '.join(locations)}")
        print(f"Max jobs per search: {max_jobs_per_search}, Total limit: {max_jobs_total}")

        all_jobs = []
        search_count = 0
        total_searches = len(posts) * len(locations)
        
        # Define signal handler for graceful shutdown
        def signal_handler(signum, frame):
            print(f"\n⚠️ Received signal {signum}. Saving collected data and shutting down gracefully...")
            self.shutdown_requested = True
        
        # Register signal handlers
        original_sigint = signal.signal(signal.SIGINT, signal_handler)
        original_sigterm = signal.signal(signal.SIGTERM, signal_handler)

        # Open browser once for all searches
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)

            try:
                # Step 1: Scrape jobs for all combinations
                for post_name in posts:
                    if self.shutdown_requested:
                        print("Shutdown requested. Stopping scraping...")
                        break
                    
                    for location_name in locations:
                        if self.shutdown_requested:
                            print("Shutdown requested. Stopping scraping...")
                            break
                        
                        search_count += 1
                        print(f"\n{'='*60}")
                        print(f"Search {search_count}/{total_searches}: '{post_name}' in '{location_name}'")
                        print(f"{'='*60}")
                        
                        # Check if we've reached the total limit
                        if len(all_jobs) >= max_jobs_total:
                            print(f"Reached total job limit: {max_jobs_total}")
                            break
                        
                        # Calculate remaining jobs for this search
                        remaining_jobs = max_jobs_total - len(all_jobs)
                        jobs_per_search = min(max_jobs_per_search, remaining_jobs)
                        
                        try:
                            jobs = await self.scrape_linkedin_jobs(page, post_name, location_name, jobs_per_search)
                            
                            if jobs:
                                # Add search metadata to each job
                                for job in jobs:
                                    job['search_post'] = post_name
                                    job['search_location'] = location_name
                                
                                all_jobs.extend(jobs)
                                self.collected_jobs = all_jobs.copy()  # Track collected jobs
                                print(f"✓ Found {len(jobs)} jobs for '{post_name}' in '{location_name}'")
                            else:
                                print(f"⚠️ No jobs found for '{post_name}' in '{location_name}'")
                                
                        except Exception as e:
                            print(f"✗ Error scraping '{post_name}' in '{location_name}': {e}")
                            continue
                        
                        # Add delay between searches to avoid rate limiting
                        if search_count < total_searches:
                            await self.random_delay(5, 10)  # 5-10 second delay between searches
                    
                    if len(all_jobs) >= max_jobs_total:
                        break

            except KeyboardInterrupt:
                print(f"\n⚠️ Keyboard interrupt detected. Saving {len(all_jobs)} collected jobs...")
            finally:
                # Restore original signal handlers
                signal.signal(signal.SIGINT, original_sigint)
                signal.signal(signal.SIGTERM, original_sigterm)
                await context.close()
                await browser.close()

        if not all_jobs:
            print("No jobs found in any search!")
            return []

        print(f"\n✓ Total scraped {len(all_jobs)} jobs from {search_count} searches")

        # Step 2: Apply title filtering BEFORE fetching full descriptions
        if self.use_filter and self.filter_manager:
            print(f"\n🔍 Applying title filter...")
            matched_jobs, rejected_jobs, filter_stats = self.apply_title_filter(all_jobs)
            
            self.filter_manager.print_filter_stats(filter_stats)
            
            if not matched_jobs:
                print("❌ No jobs matched the filter criteria")
                # Still save even if no matches
                if all_jobs:
                    await self.save_results(all_jobs)
                return []
            
            print(f"✓ {len(matched_jobs)} jobs matched filter")
            print(f"✗ {len(rejected_jobs)} jobs rejected (not relevant)")
            all_jobs = matched_jobs

        # Step 3: Filter duplicates (if database is available)
        all_jobs, duplicate_count = await self.filter_new_jobs(all_jobs)
        if duplicate_count > 0:
            print(f"\n🔄 Filtered out {duplicate_count} duplicate jobs")

        # Step 4: Save results to database
        await self.save_results(all_jobs)

        # Show sample
        self.print_sample(all_jobs)

        return all_jobs