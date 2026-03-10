import asyncio
import os
import django
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_service.settings')
django.setup()

from scraper_manager.scrapers.finnair_scraper import FinnairScraper
from scraper_manager.config import CONFIG

async def test():
    # Configure logging to see info messages
    logging.basicConfig(level=logging.INFO)
    scraper = FinnairScraper(CONFIG)
    scraper.max_jobs = 3
    
    print("Testing Finnair Scraper...")
    jobs = await scraper.fetch_jobs()
    print(f"\nExtracted {len(jobs)} jobs")
    for job in jobs:
        print(f"- {job['title']} ({job['location']})")
        print(f"  URL: {job['url']}")
        print(f"  Desc length: {len(job.get('description', ''))}")
        # if job.get('description'):
        #     print(f"  Desc snippet: {job['description'][:100]}...")

if __name__ == "__main__":
    asyncio.run(test())
