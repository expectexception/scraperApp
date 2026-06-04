import asyncio
import logging
logging.basicConfig(level=logging.INFO)
from scraper_manager.config import CONFIG
from scraper_manager.scrapers.dayforce_scraper import DayforceScraper

async def run():
    scraper = DayforceScraper(CONFIG, site_key="perimeter")
    scraper.max_jobs = 3 # limit for testing
    jobs = await scraper.fetch_jobs()
    print(f"Scraped {len(jobs)} jobs.")
    for j in jobs[:2]:
        print(j['title'], "-", j['location'])
        print(j['url'])

asyncio.run(run())
