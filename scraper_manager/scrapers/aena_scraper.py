import asyncio
import logging
from datetime import datetime
from playwright.async_api import async_playwright
import re

from .base_scraper import BaseScraper
from .job_schema import get_job_dict

logger = logging.getLogger(__name__)

class AenaScraper(BaseScraper):
    """
    Scraper for Aena Empleo (Spain)
    URL: https://empleo.aena.es/empleo/PFSrv?accion=inicio&SEDE=0
    """
    
    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key='aena', db_manager=db_manager)
        self.base_url = "https://empleo.aena.es/empleo/PFSrv?accion=inicio&SEDE=0"
        self.company_name = "Aena"

    async def fetch_jobs(self) -> list:
        from curl_cffi import requests
        jobs = []
        
        try:
            logger.info(f"[{self.site_key}] Fetching listing using curl_cffi impersonation...")
            resp = requests.get(self.base_url, impersonate="chrome110", timeout=30)
            if resp.status_code != 200:
                logger.error(f"[{self.site_key}] Failed to fetch listing: {resp.status_code}")
                return []
            
            # Fallback regex for ANY recruitment process link
            matches = re.findall(r'href=[\'"]?([^\'"]*PFSrv[^\'"]*accion=(?:seleccionar|inicio|detallar)[^\'"]*)[\'"]?[^>]*>([^<]+)</a>', resp.text, re.I)
            logger.info(f"[{self.site_key}] Found {len(matches)} potential recruitment links")
            
            for href, title in matches:
                if self.max_jobs and len(jobs) >= self.max_jobs:
                    break
                
                if not self.is_job_link(title, href):
                    continue
                
                full_url = f"https://empleo.aena.es/empleo/{href}" if 'http' not in href else href
                
                # Extract ID from URL if possible, else use title slug
                match = re.search(r'idProceso=(\d+)', href)
                jid = match.group(1) if match else re.sub(r'[^a-zA-Z0-9]', '_', title.lower())
                
                job = get_job_dict(
                    job_id=f"aena_{jid}",
                    title=title.strip(),
                    company=self.company_name,
                    location="Spain",
                    url=full_url,
                    source_url=self.base_url,
                    description=f"Aena recruitment process: {title.strip()}",
                    apply_url=full_url,
                    posted_date=datetime.now().isoformat(),
                    source=self.site_key
                )
                jobs.append(job)
        except Exception as e:
            logger.error(f"[{self.site_key}] Error: {e}")
            
        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        jobs = [j for j in jobs if j is not None]
        await self.save_results(jobs)
        return jobs
