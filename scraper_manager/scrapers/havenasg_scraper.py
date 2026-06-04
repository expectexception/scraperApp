import asyncio
import logging
import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class HavenAsgScraper(BaseScraper):
    """
    Scraper for Haven Aviation Services Group.
    URL: https://www.havenasg.com/careers
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='havenasg', db_manager=db_manager)
        self.base_url = "https://www.havenasg.com/careers"
        self.company_name = "Haven ASG"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Fetching {self.base_url}...")
        
        try:
            response = await self.make_request(self.base_url)
            if response.status_code != 200:
                logger.error(f"[{self.site_key}] Failed to fetch page. Status: {response.status_code}")
                return jobs
                
            logger.info(f"[{self.site_key}] Response length: {len(response.text)}")
            logger.debug(f"[{self.site_key}] Snippet: {response.text[:500]}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # The site uses Tailwind CSS classes like card-glass
            cards = soup.find_all('div', class_=lambda c: c and 'card-glass' in c)
            logger.info(f"[{self.site_key}] Found {len(cards)} card-glass blocks")
            
            for card in cards:
                # Find category which is in an h3 tag
                h3 = card.find('h3')
                if not h3:
                    continue
                    
                category = h3.text.strip()
                if not category:
                    continue
                    
                # Skip informative cards that aren't job lists (they lack a ul)
                ul = card.find('ul')
                if not ul:
                    logger.debug(f"[{self.site_key}] No ul found for category '{category}', skipping")
                    continue
                    
                logger.info(f"[{self.site_key}] Found job category: {category}")
                
                # The location/subtitle is in the p tag immediately following the h3
                subtitle_p = h3.find_next_sibling('p')
                location = subtitle_p.text.strip() if subtitle_p else "Unknown"
                    
                list_items = ul.find_all('li')
                roles = []
                for item in list_items:
                    spans = item.find_all('span')
                    if len(spans) > 1:
                        text = spans[1].text.strip()
                    else:
                        text = item.text.strip().lstrip('•').strip()
                        
                    if text:
                        roles.append(f"• {text}")
                
                if not roles:
                    continue
                    
                # Description contains all the roles
                roles_text = "\n".join(roles)
                full_desc = f"Roles available:\n{roles_text}\n\nTo apply, please use the contact form on the careers page."
                
                job_id_str = f"havenasg_{category}_{location}"
                job_id = f"haven_{hash(job_id_str)}"
                
                job = get_job_dict(
                    job_id=job_id,
                    title=category,
                    company=self.company_name,
                    location=location,
                    url=self.base_url + "#roles",
                    source_url=self.base_url,
                    description=full_desc,
                    apply_url=self.base_url,
                    source=self.site_key
                )
                jobs.append(job)
                    
        except Exception as e:
            logger.error(f"[{self.site_key}] Error scraping Haven ASG: {e}", exc_info=True)
            
        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        
        if self.use_filter and self.filter_manager and jobs:
            logger.info(f"[{self.site_key}] Applying final filter check...")
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)

        await self.save_results(jobs)
        return jobs
