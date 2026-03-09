"""
AAP Aviation Scraper - Job board scraper
Extracts aviation job listings from jobs.aapaviation.com
"""

import asyncio
import re
from datetime import datetime
from urllib.parse import urljoin
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict


class AAPAviationScraper(BaseScraper):
    """Scraper for AAP Aviation jobs"""
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, 'aap', db_manager=db_manager)
        self.site_config = config['sites']['aap']
        self.base_url = self.site_config['base_url']
        self.jobs_url = self.site_config['jobs_url']

    def _make_absolute_url(self, url):
        """Convert relative URL to absolute URL"""
        if not url:
            return url
        if url.startswith('http'):
            return url
        return urljoin(self.base_url, url)
        
    async def run(self):
        """Main execution method"""
        self.print_header()
        
        print(f"Fetching jobs from {self.site_config['name']}...")
        print(f"URL: {self.jobs_url}\n")
        
        jobs_raw = await self.fetch_jobs_from_listing()
        
        # Convert jobs to schema format with defensive handling
        jobs = []
        for job in jobs_raw:
            try:
                formatted_job = get_job_dict(**job)
                jobs.append(formatted_job)
            except TypeError as e:
                if 'job_id' in str(e):
                    # Fallback: remove job_id if it causes issues and retry
                    job_copy = job.copy()
                    job_id = job_copy.pop('job_id', None)
                    formatted_job = get_job_dict(**job_copy)
                    if job_id:
                        formatted_job['job_id'] = job_id
                    jobs.append(formatted_job)
                else:
                    print(f"Error formatting job: {e}")
                    continue
        
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
    
    async def fetch_jobs_from_listing(self):
        """Fetch jobs from listing page"""
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                print("Loading jobs page...")
                await self.random_delay(1, 2)
                # Use networkidle to wait for Quasar hydration
                try:
                    await page.goto(self.jobs_url, wait_until='networkidle', timeout=30000)
                except:
                    await page.goto(self.jobs_url, wait_until='domcontentloaded', timeout=30000)
                
                # Wait for dynamic content to load
                await self.random_delay(4, 6)
                
                # Loop to scroll and load jobs until we have enough
                print(f"  Starting scroll loop (Target: {self.max_jobs or 'Unlimited'} jobs)...")
                seen_count = 0
                no_new_content_count = 0
                
                while True:
                    # Scroll to bottom
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2) # Short wait for trigger
                    
                    # Scroll up a bit to trigger some lazy loaders
                    await page.evaluate("window.scrollBy(0, -500)")
                    await asyncio.sleep(1)
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    
                    # Wait for network idle or timeout using wait_for_load_state isn't reliable for infinite scroll
                    # So we just wait a bit
                    await self.random_delay(2, 3)
                    
                    # Check current job count on page
                    # Try multiple selectors to count
                    current_elements = []
                    for sel in ['a.job-tile', '.job-tile', '.q-card', 'article']:
                        els = await page.query_selector_all(sel)
                        if els:
                            current_elements = els
                            break
                    
                    current_count = len(current_elements)
                    print(f"  Current visible jobs: {current_count}")
                    
                    if current_count > seen_count:
                        seen_count = current_count
                        no_new_content_count = 0
                    else:
                        no_new_content_count += 1
                        print(f"  No new jobs loaded (Attempt {no_new_content_count}/3)")
                    
                    # Break conditions
                    if self.max_jobs and current_count >= self.max_jobs:
                        print("  Reached max_jobs limit")
                        break
                        
                    if no_new_content_count >= 3:
                        print("  No new content after multiple scrolls")
                        break
                        
                    # Safety break
                    if current_count > 500: # Hard safety limit
                        print("  Reached hard safety limit (500 jobs)")
                        break
                
                await page.evaluate("window.scrollTo(0, 0)")
                
                print("✓ Page loaded, extracting jobs...")
                
                # Try multiple selectors for job cards
                selectors = [
                    'a.job-tile',  # Verified selector from inspection
                    '.job-tile',
                    '.q-card',
                    'article'
                ]
                job_elements = []
                used_selector = None
                
                for selector in selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=5000)
                        elements = await page.query_selector_all(selector)
                        if elements and len(elements) > 0:
                            print(f"✓ Found {len(elements)} jobs using selector: {selector}")
                            job_elements = elements
                            used_selector = selector
                            break
                    except:
                        continue
                
                if not job_elements:
                    print("❌ No job elements found with known selectors")
                    # Try to get any links with /job in them
                    job_links = await page.query_selector_all('a[href*="/job"]')
                    if job_links:
                        print(f"✓ Found {len(job_links)} job links as fallback")
                        for link in job_links[:self.max_jobs] if self.max_jobs else job_links:
                            try:
                                href = await link.get_attribute('href')
                                text = await link.inner_text()
                                if href and text:
                                    job_data = self._create_basic_job(href, text.strip(), len(jobs))
                                    jobs.append(job_data)
                            except Exception as e:
                                continue
                    await browser.close()
                    return jobs
                
                # Extract job data from elements
                for idx, element in enumerate(job_elements):
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                    
                    try:
                        job_data = await self._extract_job_from_card(element, idx)
                        if job_data:
                            jobs.append(job_data)
                    except Exception as e:
                        print(f"Error extracting job {idx + 1}: {e}")
                
            except asyncio.TimeoutError:
                print("❌ Timeout loading page")
            except Exception as e:
                print(f"❌ Error fetching jobs: {e}")
            finally:
                await context.close()
                await browser.close()
        
        return jobs
    
    async def _extract_job_from_card(self, element, index):
        """Extract job details from a card element"""
        try:
            # Check if element is a link itself (for .job-tile)
            tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
            if tag_name == 'a':
                link_elem = element
            else:
                link_elem = await element.query_selector('a')
            
            if not link_elem:
                # If no link, maybe the card itself is clickable via JS, try getting link from parent or children
                link_elem = await element.query_selector('a[href]')
                if not link_elem:
                     return None
            
            url = await link_elem.get_attribute('href')
            if not url:
                return None
                
            full_url = self._make_absolute_url(url)
            
            # Generate a job_id
            job_id = f"aap_{index + 1}_{datetime.now().strftime('%Y%m%d')}"

            # Extract title
            # Selector: a.job-tile div[role='listitem'] > div:first-child > div:first-child
            title_el = await element.query_selector("div[role='listitem'] > div > div")
            if not title_el:
                title_el = await element.query_selector(".text-h6") # fallback
            
            title = await title_el.inner_text() if title_el else ""
            if not title:
                 # Fallback
                 title = await link_elem.inner_text()
            
            title = title.strip()

            # Extract location
            # Selector: a.job-tile > div:nth-child(2) > div > div:nth-child(2) > div
            location = "Unknown"
            
            try:
                # Based on inspection: Title is first, then Type/Loc blocks
                # We can try to get the text content of the second main div
                # Structure seems to be: Title Div, Then Details Div
                all_text = await element.inner_text()
                lines = [l.strip() for l in all_text.split('\n') if l.strip()]
                
                # Title is usually lines[0]
                # lines[1] might be Job Type (Permanent) or Location
                if len(lines) > 1:
                    if lines[1] not in ['Permanent', 'Contract', 'Temporary']:
                         location = lines[1]
                    elif len(lines) > 2:
                         location = lines[2]
            except:
                pass

             # Extract job type
            job_type = "Permanent" # Default
            for chip in await element.query_selector_all('.q-chip__content'):
                 text = await chip.inner_text()
                 if text in ['Permanent', 'Temporary', 'Contract']:
                     job_type = text
                     break
            
            return {
                'job_id': job_id,
                'title': title,
                'company': 'AAP Aviation',
                'location': location,
                'job_type': job_type,
                'posted_date': datetime.now().strftime('%Y-%m-%d'),
                'url': full_url,
                'source': self.site_config.get('name', 'AAP Aviation'),
                'description': '', # Will be fetched later
                'apply_url': full_url
            }
        except Exception as e:
            print(f"Error extracting job from card: {e}")
            return None
    
    def _create_basic_job(self, url, title, idx):
        """Create basic job data from URL and title"""
        if url.startswith('/'):
            url = f"{self.base_url}{url}"
        
        job_id = f"aap_{idx + 1}_{datetime.now().strftime('%Y%m%d')}"
        
        return {
            'job_id': job_id,
            'title': title,
            'company': 'AAP Aviation',
            'source': 'aap',
            'url': url,
            'apply_url': url,
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
    
    async def fetch_job_descriptions(self, jobs):
        """Fetch detailed descriptions for each job"""
        print(f"\nFetching detailed descriptions for {len(jobs)} jobs...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            
            for i in range(0, len(jobs), self.batch_size):
                batch = jobs[i:i + self.batch_size]
                tasks = []
                
                for job in batch:
                    if job.get('url') and job['url'] != self.jobs_url:
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
        """Extract detailed description from job page"""
        try:
            page, context = await self.setup_stealth_page(browser)
            
            # Set longer timeout and wait for full load
            await self.random_delay(1, 2)
            await page.goto(job['url'], wait_until='load', timeout=30000)
            
            # Wait longer for dynamic content
            await self.random_delay(4, 6)
            await self.simulate_human_behavior(page)
            
            # Get page title for better job title
            page_title = await page.title()
            if page_title and len(page_title) > len(job['title']):
                job['title'] = page_title.strip()
            
            # Extract all headings for better structure
            headings = await page.query_selector_all('h1, h2, h3, h4')
            heading_texts = []
            for h in headings:
                text = await h.inner_text()
                if text.strip():
                    heading_texts.append(text.strip())
            
            # Extract all paragraphs for description
            paragraphs = await page.query_selector_all('p')
            paragraph_texts = []
            for p in paragraphs:
                text = await p.inner_text()
                if text.strip() and len(text.strip()) > 20:  # Skip short/empty paragraphs
                    paragraph_texts.append(text.strip())
            
            # Extract lists (requirements often in lists)
            lists = await page.query_selector_all('ul, ol')
            list_texts = []
            for lst in lists:
                items = await lst.query_selector_all('li')
                if items:
                    list_items = []
                    for item in items:
                        text = await item.inner_text()
                        if text.strip():
                            list_items.append(f"• {text.strip()}")
                    if list_items:
                        list_texts.append('\n'.join(list_items))
            
            # Build comprehensive description
            description_parts = []
            
            # Add headings context
            if heading_texts:
                description_parts.append("=== Job Overview ===")
                description_parts.extend(heading_texts[:3])
                description_parts.append("")
            
            # Add paragraphs (main content)
            if paragraph_texts:
                description_parts.append("=== Description ===")
                description_parts.extend(paragraph_texts)
                description_parts.append("")
            
            # Add lists (requirements/qualifications)
            if list_texts:
                description_parts.append("=== Requirements & Details ===")
                description_parts.extend(list_texts)
            
            # Combine all parts
            if description_parts:
                job['description'] = '\n'.join(description_parts)
            
            # If still no description, try main content area
            if not job['description'] or len(job['description']) < 100:
                main_selectors = ['main', 'article', '.content', '.container']
                for selector in main_selectors:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.inner_text()
                        if len(text) > 200:
                            job['description'] = text.strip()
                            break
            
            # Fallback: use base scraper description helper
            if not job['description'] or len(job['description']) < 100:
                try:
                    fallback_desc = await self.extract_description_from_page(page)
                    if fallback_desc and len(fallback_desc) > len(job['description']):
                        job['description'] = fallback_desc
                except Exception:
                    pass
            
            # Extract location from page if not already set
            if not job.get('location') or job.get('location') == 'Unknown':
                # First try specific selectors
                location_selectors = [
                    '[class*="location"]', 
                    '[class*="Location"]',
                    '.location',
                    '[data-location]',
                    'span:has-text("Dublin")',
                    'span:has-text("Ireland")',
                    'span:has-text("Copenhagen")',
                    'span:has-text("Oslo")',
                    'span:has-text("Stockholm")',
                ]
                for selector in location_selectors:
                    try:
                        elem = await page.query_selector(selector)
                        if elem:
                            text = await elem.inner_text()
                            if text.strip() and text.strip() != 'Unknown':
                                job['location'] = text.strip()
                                break
                    except:
                        continue
                
                # If still no location, extract from description text
                if not job.get('location') or job.get('location') == 'Unknown':
                    desc_text = job.get('description', '')
                    title_text = job.get('title', '')
                    
                    # Look for location patterns in description and title
                    location_patterns = [
                        r'Dublin,\s*Ireland',
                        r'Ireland',
                        r'Copenhagen,\s*Denmark', 
                        r'Denmark',
                        r'Oslo,\s*Norway',
                        r'Norway',
                        r'Stockholm,\s*Sweden',
                        r'Sweden',
                        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # City, Country
                        r'Location:\s*([^\n\r]+)',
                        r'Based in\s+([^\n\r]+)',
                        r'([A-Z][a-z]+\s*,\s*[A-Z][a-z]+)',  # City, Country
                    ]
                    
                    # Check title first (often contains location)
                    for pattern in location_patterns:
                        match = re.search(pattern, title_text, re.IGNORECASE)
                        if match:
                            location = match.group(1) if len(match.groups()) > 0 else match.group(0)
                            if len(location.strip()) > 2 and len(location.strip()) < 50:
                                job['location'] = location.strip()
                                break
                    
                    # Then check description
                    if not job.get('location') or job.get('location') == 'Unknown':
                        for pattern in location_patterns:
                            match = re.search(pattern, desc_text, re.IGNORECASE)
                            if match:
                                location = match.group(1) if len(match.groups()) > 0 else match.group(0)
                                if len(location.strip()) > 2 and len(location.strip()) < 50:
                                    job['location'] = location.strip()
                                    break
            
            # Extract job type
            if not job['job_type']:
                type_keywords = ['Permanent', 'Contract', 'Temporary', 'Full-time', 'Part-time', 'Hourly']
                body_text = await page.inner_text('body')
                for keyword in type_keywords:
                    if keyword in body_text:
                        job['job_type'] = keyword
                        break
            
            # Extract deadline/closing date
            deadline_selectors = [
                '[class*="deadline"]',
                '[class*="closing"]',
                'span:has-text("Deadline")',
                'span:has-text("ASAP")',
            ]
            for selector in deadline_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        text = await elem.inner_text()
                        if text.strip():
                            job['closing_date'] = text.strip()
                            break
                except:
                    continue
            
            # Extract department/category
            category_selectors = [
                '[class*="category"]',
                '[class*="department"]',
                'span:has-text("Cabin Crew")',
            ]
            for selector in category_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        text = await elem.inner_text()
                        if text.strip():
                            job['department'] = text.strip()
                            break
                except:
                    continue
            
            # Extract posted date - try multiple approaches
            if not job.get('posted_date'):
                # Try JSON-LD first
                try:
                    scripts = await page.query_selector_all('script[type="application/ld+json"]')
                    for s in scripts:
                        try:
                            json_text = await s.inner_text()
                            import json as _json
                            data = _json.loads(json_text)
                            items = data if isinstance(data, list) else [data]
                            for item in items:
                                if isinstance(item, dict) and item.get('datePosted'):
                                    posted_candidate = item.get('datePosted')
                                    parsed = self.parse_posted_date(posted_candidate)
                                    job['posted_date'] = parsed if parsed else posted_candidate
                                    break
                        except Exception:
                            continue
                except Exception:
                    pass

                # Try meta tags and page patterns
                if not job.get('posted_date'):
                    date_patterns = [
                        r'Posted[:\s]+([^\n\r]+)',
                        r'Date Posted[:\s]+([^\n\r]+)',
                        r'Published[:\s]+([^\n\r]+)',
                        r'Posted on[:\s]+([^\n\r]+)',
                    ]
                    body_text = await page.inner_text('body')
                    for pattern in date_patterns:
                        match = re.search(pattern, body_text, re.IGNORECASE)
                        if match:
                            date_text = match.group(1).strip()
                            parsed = self.parse_posted_date(date_text)
                            job['posted_date'] = parsed if parsed else date_text
                            break

                # Fallback: use base scraper helpers
                if not job.get('posted_date'):
                    try:
                        fallback_pd = await self.extract_posted_date_from_page(page)
                        if fallback_pd:
                            job['posted_date'] = fallback_pd
                    except Exception:
                        pass
                
                # Final fallback: set current date if no posted date found
                # This is reasonable for aviation jobs that don't specify posting dates
                if not job.get('posted_date'):
                    from datetime import datetime
                    job['posted_date'] = datetime.now().date().isoformat()
            
            await page.close()
            await context.close()
            
        except asyncio.TimeoutError:
            print(f"  Timeout for {job['job_id']}")
        except Exception as e:
            print(f"  Error fetching description for {job['job_id']}: {e}")
