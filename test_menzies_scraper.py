import asyncio
import logging
logging.basicConfig(level=logging.INFO)
from scraper_manager.config import CONFIG
from scraper_manager.scrapers.menzies_scraper import MenziesScraper

async def run():
    scraper = MenziesScraper(CONFIG)
    scraper.max_jobs = 3 # limit for testing
    jobs = await scraper.fetch_jobs()
    print(f"Scraped {len(jobs)} jobs.")

asyncio.run(run())
