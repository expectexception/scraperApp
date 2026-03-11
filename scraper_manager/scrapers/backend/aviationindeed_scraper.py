"""
Aviation Indeed Scraper - CEIPAL-based job board
Handles iframe-embedded job listings from CEIPAL API
"""

import asyncio
import json
import re
import logging
from datetime import datetime
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class AviationIndeedScraper(BaseScraper):
    """Scraper for Aviation Indeed (Next.js & CEIPAL based)"""
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, 'aviationindeed', db_manager=db_manager)
        self.site_config = config['sites'].get('aviationindeed', {})
        self.base_url = self.site_config.get('base_url', 'https://www.aviationindeed.com')
        self.ceipal_url = self.site_config.get('ceipal_url', '')
        
    async def run(self):
        """Main execution method"""
        self.print_header()
        
        print(f"Fetching jobs from {self.site_config.get('name', 'Aviation Indeed')}...")
        print(f"URL: {self.base_url}/jobs/\n")
        
        # New layout: use direct page scraping or __NEXT_DATA__
        jobs = await self.fetch_jobs_current_layout()
        
        if not jobs:
            print("❌ No jobs found with current layout – falling back to legacy iframe check")
            # In runtime, try simple Playwright load if first attempt failed
            pass
        
        if not jobs:
            print("❌ Still no jobs found")
            return []
        
        print(f"\n✓ Extracted {len(jobs)} jobs")
        
        # Save results (BaseScraper method)
        await self.save_results(jobs, self.site_config.get('name', 'Aviation Indeed'))
        self.print_sample(jobs)
        
        return jobs

    async def fetch_jobs_current_layout(self):
        """Fetch jobs from the new Aviation Indeed layout (Next.js) using __NEXT_DATA__"""
        jobs = []
        jobs_url = f"{self.base_url}/jobs/"
        
        print(f"Fetching {jobs_url} via robust JSON extractor...")
        
        try:
            # Use make_request with impersonation to get the raw HTML
            response = await self.make_request(jobs_url)
            if not response or response.status_code != 200:
                print(f"❌ make_request failed: {response.status_code if response else 'No response'}")
                return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find Next.js data script
            next_data_script = soup.find('script', id='__NEXT_DATA__')
            if next_data_script:
                try:
                    data = json.loads(next_data_script.string)
                    # Traverse the props to find jobs list
                    page_props = data.get('props', {}).get('pageProps', {})
                    jobs_list = page_props.get('jobs', [])
                    
                    if not jobs_list:
                        # Try finding in dehydratedState (React Query)
                        queries = page_props.get('dehydratedState', {}).get('queries', [])
                        for q in queries:
                            res = q.get('state', {}).get('data', {})
                            if isinstance(res, list) and len(res) > 0 and (len(res) > 0 and ('title' in res[0] or 'job_title' in res[0])):
                                jobs_list = res
                                break
                            elif isinstance(res, dict) and 'jobs' in res:
                                jobs_list = res['jobs']
                                break

                    if jobs_list:
                        print(f"✓ Extracted {len(jobs_list)} jobs from __NEXT_DATA__")
                        for idx, job in enumerate(jobs_list):
                            if self.max_jobs and len(jobs) >= self.max_jobs:
                                break
                                
                            title = job.get('title', job.get('job_title', 'Unknown Position'))
                            job_data_id = str(job.get('id', job.get('job_id', f'aviation_{idx}')))
                            location = job.get('location', job.get('job_location', 'Remote/Global'))
                            posted_date = job.get('posted_at', job.get('created_at', ''))
                            
                            slug = job.get('slug', '')
                            url = f"{self.base_url}/jobs/{slug}" if slug else jobs_url
                            
                            jobs.append({
                                'job_id': job_data_id,
                                'title': title,
                                'company': 'Aviation Indeed',
                                'source': self.site_key,
                                'url': url,
                                'apply_url': url,
                                'location': location,
                                'posted_date': posted_date,
                                'description': job.get('description', 'See website for details'),
                                'timestamp': datetime.now().isoformat(),
                            })
                        
                        if jobs: return jobs
                except Exception as e:
                    print(f"⚠️ Error parsing __NEXT_DATA__: {e}")
            
            # Fallback to direct HTML article parsing if script is missing or empty
            articles = soup.find_all('article')
            if articles:
                print(f"✓ Found {len(articles)} articles in raw HTML")
                for idx, article in enumerate(articles):
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                    h3 = article.find('h3')
                    title = h3.get_text(strip=True) if h3 else f"Aviation Job {idx + 1}"
                    if not title or len(title) < 4:
                        continue

                    # Extract the most specific per-job URL from anchor tags
                    job_url = jobs_url  # default fallback
                    for a_tag in article.find_all('a', href=True):
                        href = a_tag['href']
                        full_href = urljoin(self.base_url, href)
                        # Prefer links that look like job detail pages
                        if href and href not in ('/', '#', '') and 'jobs/' in href.lower():
                            job_url = full_href
                            break
                    # If still listing URL, try any non-trivial link
                    if job_url == jobs_url:
                        for a_tag in article.find_all('a', href=True):
                            href = a_tag['href']
                            if href and href not in ('/', '#', '') and not href.startswith('mailto'):
                                job_url = urljoin(self.base_url, href)
                                break

                    # Try to extract company name from article text
                    company = 'Aviation Indeed'
                    p_tags = article.find_all('p')
                    desc_text = ' '.join(p.get_text(strip=True) for p in p_tags[:3])
                    # Seed description from article text
                    description = desc_text[:500] if desc_text else ''

                    jobs.append({
                        'job_id': f"aviation_html_{idx}",
                        'title': title,
                        'company': company,
                        'source': self.site_key,
                        'url': job_url,
                        'apply_url': job_url,
                        'location': 'Unknown',
                        'description': description,
                        'timestamp': datetime.now().isoformat()
                    })
                if jobs:
                    return jobs
                
        except Exception as e:
            print(f"❌ Error in direct extraction: {e}")
            
        return []
