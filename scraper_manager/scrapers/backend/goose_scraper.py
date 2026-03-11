"""
Goose Recruitment Scraper
Extracts aviation job listings from goose-recruitment.com
"""

import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict


class GooseRecruitmentScraper(BaseScraper):
    """Scraper for Goose Recruitment"""
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, 'goose', db_manager=db_manager)
        self.site_config = config['sites']['goose']
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
                print("Loading Goose Recruitment page...")
                await self.random_delay(1, 2)
                await page.goto(self.jobs_url, wait_until='domcontentloaded', timeout=30000)
                
                # Wait for job listings to load
                await self.random_delay(4, 6)
                await self.simulate_human_behavior(page)
                print("✓ Page loaded")
                
                # Find all job links (format: /job/title-id)
                # Exclude /save_job and /apply links
                job_links = await page.query_selector_all('a[href^="/job/"]')
                print(f"✓ Found {len(job_links)} job-related links")
                
                # Extract unique job URLs
                seen_urls = set()
                for link in job_links:
                    try:
                        href = await link.get_attribute('href')
                        if not href or href in seen_urls:
                            continue
                        
                        # Skip apply and save links
                        if '/apply' in href or '/save_job' in href:
                            continue
                        
                        # Build full URL
                        job_url = f"{self.base_url}{href}"
                        seen_urls.add(href)
                        
                        # Extract title from link text
                        title = await link.inner_text()
                        title = title.strip()
                        
                        # Skip navigation links
                        if title and len(title) > 10 and title not in ['Read More', 'Apply Now', 'Save Job']:
                            job_id = href.split('/')[-1] if '/' in href else f"goose_{len(jobs)}"
                            
                            job_data = {
                                'job_id': f"goose_{job_id}",
                                'title': title,
                                'company': 'GOOSE Recruitment',
                                'source': 'goose',
                                'url': job_url,
                                'apply_url': f"{job_url}/apply",
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
        """Extract detailed description from job page"""
        try:
            page, context = await self.setup_stealth_page(browser)
            
            # Load job detail page
            await self.random_delay(1, 2)
            await page.goto(job['url'], wait_until='load', timeout=30000)
            await self.random_delay(2, 4)
            await self.simulate_human_behavior(page)
            
            # Update title from page if available
            page_title = await page.title()
            if page_title and len(page_title) > 10:
                # Clean up title
                title_clean = page_title.replace(' · GOOSE Recruitment', '').strip()
                if title_clean and title_clean != 'Aviation Jobs - Airline Jobs - Pilot Jobs':
                    job['title'] = title_clean
            
            # Extract metadata from page content
            # Format is "• Label: Value" or "Label:\nValue"
            body_text = await page.inner_text('body')
            import re
            
            # Extract location (handles both inline and newline formats)
            loc_match = re.search(r'Location[:\s]+([^\n•]+)', body_text, re.IGNORECASE)
            if loc_match:
                location = loc_match.group(1).strip()
                if location and len(location) < 100:  # Sanity check
                    job['location'] = location
            
            # Extract job type
            type_match = re.search(r'Job Type[:\s]+([^\n•]+)', body_text, re.IGNORECASE)
            if type_match:
                job_type = type_match.group(1).strip()
                if job_type and len(job_type) < 50:
                    job['job_type'] = job_type
            
            # Extract sector/department
            sector_match = re.search(r'Sector[:\s]+([^\n•]+)', body_text, re.IGNORECASE)
            if sector_match:
                department = sector_match.group(1).strip()
                if department and len(department) < 100:
                    job['department'] = department
            
            # Extract posted date
            date_match = re.search(r'(?:Posted|Date)[:\s]+([^\n•]+)', body_text, re.IGNORECASE)
            if date_match:
                date_text = date_match.group(1).strip()
                parsed_date = self.parse_posted_date(date_text)
                job['posted_date'] = parsed_date if parsed_date else date_text
            
            # Extract full description with deep extraction
            description_parts = []
            
            # Find main job description container
            desc_selectors = [
                '.job-description',
                '[class*="description"]',
                '.job-content',
                'article',
                'main',
            ]
            
            main_desc_elem = None
            for selector in desc_selectors:
                elem = await page.query_selector(selector)
                if elem:
                    text = await elem.inner_text()
                    if len(text) > 200:
                        main_desc_elem = elem
                        break
            
            if main_desc_elem:
                # Extract headings
                headings = await main_desc_elem.query_selector_all('h1, h2, h3, h4')
                heading_texts = []
                for h in headings:
                    text = (await h.inner_text()).strip()
                    if text and len(text) > 3:
                        heading_texts.append(text)
                
                if heading_texts:
                    description_parts.append("=== Job Overview ===")
                    description_parts.extend(heading_texts[:5])
                    description_parts.append("")
                
                # Extract paragraphs
                paragraphs = await main_desc_elem.query_selector_all('p')
                paragraph_texts = []
                for p in paragraphs:
                    text = (await p.inner_text()).strip()
                    if text and len(text) > 20:
                        paragraph_texts.append(text)
                
                if paragraph_texts:
                    description_parts.append("=== Description ===")
                    description_parts.extend(paragraph_texts)
                    description_parts.append("")
                
                # Fallback: If no paragraphs found, or to catch text not in p tags
                # Get all text from container if paragraph count is low
                if len(paragraph_texts) < 2:
                    # Get direct text nodes or divs that look like text
                    # We can just get the full inner_text of the container and clean it
                    full_container_text = await main_desc_elem.inner_text()
                    lines = [line.strip() for line in full_container_text.split('\n') if line.strip()]
                    
                    # Filter out lines we likely already have (headers/lists)
                    # This is tricky to do perfectly, but getting the raw text is safer than missing it.
                    # Let's append the cleaned text as a "Full Text" section if we missed paragraphs
                    if not paragraph_texts:
                         description_parts.append("=== Full Details ===")
                         description_parts.extend([l for l in lines if len(l) > 30]) # Only substantial lines
                
                # Extract lists
                lists = await main_desc_elem.query_selector_all('ul, ol')
                list_texts = []
                for lst in lists:
                    items = await lst.query_selector_all('li')
                    if items:
                        list_items = []
                        for item in items[:20]:
                            text = (await item.inner_text()).strip()
                            if text:
                                list_items.append(f"• {text}")
                        if list_items:
                            list_texts.append('\n'.join(list_items))
                
                if list_texts:
                    description_parts.append("=== Requirements & Details ===")
                    description_parts.extend(list_texts)
            
            # Combine all parts
            if description_parts:
                job['description'] = '\n'.join(description_parts)
            
            # Fallback: Get full text if description is still empty
            if not job['description'] or len(job['description']) < 100:
                body_text = await page.inner_text('body')
                if len(body_text) > 300:
                    job['description'] = body_text[:3000]  # Limit to reasonable size
            
            await page.close()
            await context.close()
            
        except asyncio.TimeoutError:
            print(f"  Timeout for {job['job_id']}")
        except Exception as e:
            print(f"  Error fetching description for {job['job_id']}: {e}")
