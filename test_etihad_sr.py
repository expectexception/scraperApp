import asyncio
import logging
logging.basicConfig(level=logging.INFO)
from scraper_manager.config import CONFIG
from scraper_manager.scrapers.smartrecruiters_scraper import SmartRecruitersScraper

async def run():
    scraper = SmartRecruitersScraper(CONFIG, site_key="etihad")
    scraper.max_jobs = 3 # limit for testing
    jobs = await scraper.fetch_jobs()
    print(f"Scraped {len(jobs)} jobs.")
    for j in jobs[:2]:
        print(j['title'], "-", j['location'])
        print(j['url'])

asyncio.run(run())
