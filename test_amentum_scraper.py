import asyncio
from scraper_manager.config import CONFIG
from scraper_manager.scrapers.amentum_scraper import AmentumScraper

async def run():
    scraper = AmentumScraper(CONFIG)
    scraper.max_jobs = 5 # limit for testing
    jobs = await scraper.fetch_jobs()
    print(f"Scraped {len(jobs)} jobs.")
    for j in jobs[:2]:
        print(j['title'], "-", j['location'])
        print(j['description'][:100] + "...")

asyncio.run(run())
