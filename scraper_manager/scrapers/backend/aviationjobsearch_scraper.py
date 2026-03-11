"""
Aviation Job Search Scraper
Extracts aviation job listings from aviationjobsearch.com
"""

import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict


class AviationJobSearchScraper(BaseScraper):
    """Scraper for Aviation Job Search"""
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, 'aviationjobsearch', db_manager=db_manager)
        self.site_config = config['sites']['aviationjobsearch']
        self.base_url = self.site_config['base_url']
        self.jobs_url = self.site_config['jobs_url']
        
    async def run(self):
        """Main execution method"""
        self.print_header()
        
        print(f"Fetching jobs from {self.site_config['name']}...")
        print(f"URL: {self.jobs_url}\n")
        
        jobs_raw = await self.fetch_jobs_from_listing()
        jobs = [get_job_dict(**job) for job in jobs_raw]
        
        if not jobs:
            print("❌ No jobs found")
            return []
        
        print(f"\n✓ Extracted {len(jobs)} jobs from listing")
        
        # Apply title filtering BEFORE fetching descriptions (saves time)
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
        
        # Print sample and category summary
        self.print_sample(jobs_with_descriptions)
        self.print_category_summary(jobs_with_descriptions)
        
        return jobs_with_descriptions
    
    def print_category_summary(self, jobs):
        """Print summary of jobs organized by category"""
        if not jobs:
            return
        
        # Filter jobs that matched
        matched_jobs = [j for j in jobs if j.get('filter_match')]
        if not matched_jobs:
            return
        
        print(f"\n{'='*70}")
        print(f"📊 JOBS BY CATEGORY ({len(matched_jobs)} matched jobs)")
        print(f"{'='*70}\n")
        
        # Group by primary category
        by_category = {}
        for job in matched_jobs:
            primary = job.get('primary_category', 'Uncategorized')
            if primary not in by_category:
                by_category[primary] = []
            by_category[primary].append(job)
        
        # Print each category
        for category, cat_jobs in sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"🏷️  {category} ({len(cat_jobs)} jobs)")
            print(f"{'─'*70}")
            
            for job in cat_jobs[:10]:  # Show max 10 per category
                score = job.get('filter_score', 0.0)
                title = job.get('title', 'N/A')
                location = job.get('location', 'N/A')
                
                # Truncate title if too long
                if len(title) > 60:
                    title = title[:57] + '...'
                
                print(f"  • [{score:.1f}] {title}")
                print(f"    📍 {location}")
            
            if len(cat_jobs) > 10:
                print(f"  ... and {len(cat_jobs) - 10} more")
            print()
        
        print(f"{'='*70}\n")
    
    async def fetch_jobs_from_listing(self):
        """Fetch jobs from listing page"""
        jobs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                print("Loading Aviation Job Search page...")
                await page.goto(self.jobs_url, wait_until='domcontentloaded', timeout=30000)
                
                # Random delay after page load
                await self.random_delay(self.page_load_delay, self.page_load_delay + 2)
                
                # Simulate human behavior
                await self.simulate_human_behavior(page)
                print("✓ Page loaded")
                
                # Find all job links (format: /jobs/category/title/id)
                job_links = await page.query_selector_all('a[href*="/jobs/"]')
                print(f"✓ Found {len(job_links)} job links")
                
                # Extract unique job URLs
                seen_urls = set()
                for link in job_links:
                    try:
                        href = await link.get_attribute('href')
                        if not href or href in seen_urls:
                            continue
                        
                        # Build full URL
                        if href.startswith('/'):
                            job_url = f"{self.base_url}{href}"
                        elif href.startswith('http'):
                            job_url = href
                        else:
                            continue
                        
                        # Only process URLs that look like job pages
                        if '/jobs/' in job_url and len(href.split('/')) >= 4:
                            seen_urls.add(href)
                            
                            # Extract title from link text
                            title = await link.inner_text()
                            title = title.strip()
                            
                            if title and len(title) > 5:  # Valid title
                                job_id = href.split('/')[-1] if '/' in href else f"ajs_{len(jobs)}"
                                
                                job_data = {
                                    'job_id': f"aviationjobsearch_{job_id}",
                                    'title': title,
                                    'company': '',  # Will extract from detail page
                                    'source': 'aviationjobsearch',
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
                                
                                if self.max_jobs and len(jobs) >= self.max_jobs:
                                    break
                    
                    except Exception as e:
                        continue
                
            except Exception as e:
                print(f"❌ Error fetching jobs: {e}")
            finally:
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
        """Extract detailed description from job page"""
        try:
            page, context = await self.setup_stealth_page(browser)
            
            # Random delay before loading
            await self.random_delay(1, 2)
            
            # Load job detail page
            await page.goto(job['url'], wait_until='load', timeout=30000)
            await self.random_delay(2, 4)
            
            # Simulate human behavior
            await self.simulate_human_behavior(page)
            
            # Parse page title for job details
            # Format: "Job Title in Location by Company"
            page_title = await page.title()
            if page_title and len(page_title) > 10:
                # Clean up title
                title_clean = page_title.replace(' - Aviation Job Search', '').strip()
                
                # Parse location and company from title
                if ' in ' in title_clean and ' by ' in title_clean:
                    parts = title_clean.split(' in ')
                    job_title = parts[0].strip()
                    rest = parts[1]
                    
                    loc_comp = rest.split(' by ')
                    location = loc_comp[0].strip()
                    company = loc_comp[1].strip()
                    
                    job['title'] = job_title
                    job['location'] = location
                    job['company'] = company
                elif title_clean:
                    job['title'] = title_clean
            
            # Extract department from URL structure
            # URL format: /jobs/category/subcategory/title
            url_parts = job['url'].split('/')
            if len(url_parts) > 4:
                category = url_parts[4] if len(url_parts) > 4 else ''
                subcategory = url_parts[5] if len(url_parts) > 5 else ''
                
                # Capitalize and clean category
                if category:
                    job['department'] = category.replace('-', ' ').title()
            
            # Extract job type from page content
            # Look for employment type mentions
            page_content = await page.inner_text('body')
            content_lower = page_content.lower()
            
            # Check for employment type keywords
            if 'permanent' in content_lower:
                if 'full-time' in content_lower or 'full time' in content_lower:
                    job['job_type'] = 'Permanent, Full-Time'
                elif 'part-time' in content_lower or 'part time' in content_lower:
                    job['job_type'] = 'Permanent, Part-Time'
                else:
                    job['job_type'] = 'Permanent'
            elif 'contract' in content_lower:
                if 'full-time' in content_lower or 'full time' in content_lower:
                    job['job_type'] = 'Contract, Full-Time'
                elif 'part-time' in content_lower or 'part time' in content_lower:
                    job['job_type'] = 'Contract, Part-Time'
                else:
                    job['job_type'] = 'Contract'
            elif 'full-time' in content_lower or 'full time' in content_lower:
                job['job_type'] = 'Full-Time'
            elif 'part-time' in content_lower or 'part time' in content_lower:
                job['job_type'] = 'Part-Time'
            
            # Extract posted date
            import re
            date_patterns = [
                r'(?:posted|published)[:\s]+([^\n<]+?)(?:\n|<|$)',
                r'(?:date)[:\s]+([^\n<]+?)(?:\n|<|$)',
            ]
            for pattern in date_patterns:
                match = re.search(pattern, page_content, re.IGNORECASE)
                if match:
                    date_text = match.group(1).strip()
                    parsed_date = self.parse_posted_date(date_text)
                    job['posted_date'] = parsed_date if parsed_date else date_text
                    break
            
            # If no date found from patterns, try parsing JSON-LD (JobPosting) and date elements
            if not job['posted_date']:
                # Attempt to parse JSON-LD scripts for a JobPosting with datePosted
                try:
                    scripts = await page.query_selector_all('script[type="application/ld+json"]')
                    for s in scripts:
                        try:
                            json_text = await s.inner_text()
                            import json as _json
                            data = _json.loads(json_text)
                            # JSON-LD can be a list or a single dict
                            items = data if isinstance(data, list) else [data]
                            for item in items:
                                if isinstance(item, dict):
                                    # Check for JobPosting type or any object with datePosted
                                    item_type = item.get('@type') or item.get('type') or ''
                                    if ('JobPosting' in str(item_type) or item.get('datePosted')):
                                        if item.get('datePosted'):
                                            posted_candidate = item.get('datePosted')
                                            parsed = self.parse_posted_date(posted_candidate)
                                            job['posted_date'] = parsed if parsed else posted_candidate
                                            break
                            if job['posted_date']:
                                break
                        except Exception:
                            continue
                except Exception:
                    pass

            # If still not found, try looking for date elements in the page
            if not job['posted_date']:
                try:
                    date_elem = await page.query_selector('[class*="date"], [class*="posted"], time, [class*="Date"]')
                    if date_elem:
                        date_text = (await date_elem.inner_text()).strip()
                        parsed_date = self.parse_posted_date(date_text)
                        job['posted_date'] = parsed_date if parsed_date else date_text
                except:
                    pass

            # Additional fallback: use base scraper heuristics for posted_date
            if not job['posted_date']:
                try:
                    fallback_pd = await self.extract_posted_date_from_page(page)
                    if fallback_pd:
                        job['posted_date'] = fallback_pd
                except Exception:
                    pass

                # Additional fallback: use base heuristics to find posted date
                if not job['posted_date']:
                    try:
                        fallback_pd = await self.extract_posted_date_from_page(page)
                        if fallback_pd:
                            job['posted_date'] = fallback_pd
                    except Exception:
                        pass

            # Additional fallback: look for "X ago" or "posted" phrases anywhere on the page
            if not job['posted_date']:
                try:
                    # Prefer the main description text if available
                    search_text = ''
                    try:
                        search_text = await (main_desc_elem.inner_text() if main_desc_elem else page.inner_text('body'))
                    except:
                        search_text = await page.inner_text('body')

                    # First, look for explicit relative-time patterns like '3 days ago', '2 weeks ago'
                    m = re.search(r"(\d+\s*(?:minute|hour|day|week|month|year)s?\s+ago)", search_text, re.IGNORECASE)
                    if m:
                        parsed = self.parse_posted_date(m.group(1))
                        if parsed:
                            job['posted_date'] = parsed

                    # Next, look for lines like 'Posted: 3 days ago' or 'Posted on 01 Dec 2025'
                    if not job['posted_date']:
                        m2 = re.search(r'(?:posted|published)[:\s]+([^\n\r<]+)', search_text, re.IGNORECASE)
                        if m2:
                            dt = m2.group(1).strip()
                            parsed = self.parse_posted_date(dt)
                            job['posted_date'] = parsed if parsed else dt
                except Exception:
                    pass
            
            # Extract full description with deep extraction
            description_parts = []
            
            # Find main job description container
            desc_selectors = [
                '.job-description',
                '[class*="description"]',
                '.content',
                'article',
                'main',
            ]
            
            main_desc_elem = None
            for selector in desc_selectors:
                elem = await page.query_selector(selector)
                if elem:
                    text = await elem.inner_text()
                    # Look for substantial content (skip navigation)
                    if len(text) > 300:
                        main_desc_elem = elem
                        break
            
            if main_desc_elem:
                # Get full text content
                full_text = await main_desc_elem.inner_text()
                
                # Clean up the text
                lines = [line.strip() for line in full_text.split('\n')]
                cleaned_lines = []
                
                for line in lines:
                    # Skip navigation and UI elements
                    skip_keywords = ['share', 'save', 'apply', 'log in', 'register', 'miles', 'distance', 'search']
                    if any(keyword in line.lower() for keyword in skip_keywords) and len(line) < 30:
                        continue
                    
                    # Keep substantial content
                    if line and len(line) > 2:
                        cleaned_lines.append(line)
                
                # Join cleaned lines
                if cleaned_lines:
                    job['description'] = '\n'.join(cleaned_lines)
            
            # Fallback: Get content from body if description is empty
            if not job['description'] or len(job['description']) < 200:
                body_text = await page.inner_text('body')
                if len(body_text) > 300:
                    # Find where actual job content starts (after navigation)
                    lines = body_text.split('\n')
                    content_start = 0
                    
                    # Skip navigation lines
                    for i, line in enumerate(lines):
                        if len(line) > 50 or '✈️' in line or 'about' in line.lower():
                            content_start = i
                            break
                    
                    # Get content from that point
                    job_lines = [l.strip() for l in lines[content_start:] if l.strip() and len(l.strip()) > 2]
                    job['description'] = '\n'.join(job_lines[:100])  # Limit to 100 lines

            # Extract salary
            salary_info = await self.extract_salary_from_page(page)
            job.update(salary_info)
            
            await page.close()
            
        except asyncio.TimeoutError:
            print(f"  Timeout for {job['job_id']}")
        except Exception as e:
            print(f"  Error fetching description for {job['job_id']}: {e}")
