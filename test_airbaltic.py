import asyncio
from scraper_manager.scrapers.airbaltic_scraper import AirBalticScraper
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    s = AirBalticScraper({})
    s.max_jobs = 5
    await s.fetch_jobs()

asyncio.run(main())
