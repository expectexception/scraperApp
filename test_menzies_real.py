import asyncio
import logging
logging.basicConfig(level=logging.INFO)
from scraper_manager.config import CONFIG
from scraper_manager.scrapers.menzies_scraper import MenziesScraper

async def run():
    scraper = MenziesScraper(CONFIG)
    scraper.max_jobs = 5 # fetch more jobs to ensure we get some matches
    jobs = await scraper.run()
    
    print("\n--- RESULTS ---")
    print(f"Scraped {len(jobs)} jobs.")
    for j in jobs[:3]:
        print(f"Title: {j.get('title')}")
        print(f"Location: {j.get('location')}")
        print(f"URL: {j.get('url')}")
        print(f"Desc Preview: {j.get('description', '')[:50]}...")
        print("----------------")

asyncio.run(run())
