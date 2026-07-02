import asyncio
import logging
import json
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from .job_schema import get_job_dict
from datetime import datetime

logger = logging.getLogger(__name__)

class AirtankerScraper(BaseScraper):
    """Scraper for Airtanker"""

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="airtanker", db_manager=db_manager)
        self.site_config = config.get("sites", {}).get("airtanker", {})
        self.base_url = self.site_config.get("base_url", "https://airtanker.pinpointhq.com")
        self.jobs_url = self.site_config.get("jobs_url", "https://airtanker.pinpointhq.com/postings.json")
        self.company_name = "Airtanker"

    async def fetch_jobs(self) -> list:
        jobs = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page, context = await self.setup_stealth_page(browser)
            
            try:
                logger.info(f"[{self.site_key}] Loading jobs from {self.jobs_url}")
                response = await page.goto(self.jobs_url, wait_until="networkidle", timeout=60000)
                text = await response.text()
                
                # Check for HTML wrapper (e.g. <pre>)
                if text.strip().startswith("<"):
                    try:
                        text = await page.inner_text("pre")
                    except:
                        pass
                
                data = json.loads(text)
                postings = data.get("data", [])
                logger.info(f"[{self.site_key}] API returned {len(postings)} jobs")
                
                for item in postings:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break
                        
                    try:
                        title = item.get("title", "").strip()
                        if not title:
                            continue
                            
                        job_url = item.get("url", "")
                        if not job_url:
                            continue
                            
                        # Build Location
                        loc_data = item.get("location") or {}
                        city = loc_data.get("city") or loc_data.get("name") or ""
                        province = loc_data.get("province") or ""
                        loc_str = f"{city}, {province}".strip(", ")
                        if not loc_str:
                            loc_str = "Brize Norton, UK"
                        
                        # Build Description
                        desc_parts = []
                        if item.get("description"):
                            desc_parts.append(item["description"])
                        if item.get("key_responsibilities"):
                            desc_parts.append("Key Responsibilities:\n" + item["key_responsibilities"])
                        if item.get("skills_knowledge_expertise"):
                            desc_parts.append("Skills, Knowledge & Expertise:\n" + item["skills_knowledge_expertise"])
                        description = "\n\n".join(desc_parts).strip()
                        
                        posted_date = ""
                        closing_date = ""
                        deadline = item.get("deadline_at")
                        if deadline:
                            parsed_dl = self.parse_posted_date(deadline)
                            if parsed_dl:
                                closing_date = parsed_dl
                                
                        job_id = f"airtanker_{item.get('id')}"
                        dept = item.get("department")
                        dept_name = ""
                        if dept:
                            if isinstance(dept, dict):
                                dept_name = dept.get("name", "")
                            else:
                                dept_name = str(dept)
                        
                        jobs.append({
                            "job_id": job_id,
                            "title": title,
                            "company": self.company_name,
                            "source": self.site_key,
                            "url": job_url,
                            "apply_url": job_url,
                            "location": self.normalize_location(loc_str),
                            "timestamp": datetime.now().isoformat(),
                            "description": description,
                            "posted_date": posted_date,
                            "closing_date": closing_date,
                            "job_type": item.get("employment_type_text", ""),
                            "department": dept_name
                        })
                    except Exception as e:
                        logger.error(f"[{self.site_key}] Error parsing job item: {e}")
                        continue
            except Exception as e:
                logger.error(f"[{self.site_key}] Extraction failed: {e}")
            finally:
                await context.close()
                await browser.close()
                
        return jobs

    async def fetch_job_descriptions(self, jobs: list) -> list:
        # Descriptions already populated in fetch_jobs
        return jobs

    async def run(self):
        self.print_header()
        jobs_raw = await self.fetch_jobs()
        jobs = [get_job_dict(**job) for job in jobs_raw]
        
        if not jobs:
            return []
            
        if self.use_filter and self.filter_manager:
            jobs, _, _ = self.apply_title_filter(jobs)
            if not jobs:
                return []
                
        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []
            
        # Already has descriptions
        await self.save_results(jobs)
        return jobs
