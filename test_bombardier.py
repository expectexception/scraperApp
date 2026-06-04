import asyncio
import logging
logging.basicConfig(level=logging.INFO)
from scraper_manager.config import CONFIG
from scraper_manager.scrapers.bombardier_scraper import BombardierScraper

async def run():
    scraper = BombardierScraper(CONFIG, site_key="bombardier")
    scraper.max_jobs = 3 # limit for testing
    scraper.max_pages = 2
    jobs = await scraper.fetch_jobs()
    print(f"Scraped {len(jobs)} jobs.")
    for j in jobs[:2]:
        print(j['title'], "-", j['location'])
        print(j['url'])

asyncio.run(run())
