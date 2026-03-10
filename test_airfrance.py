import asyncio
import os
import django
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_service.settings')
django.setup()

from scraper_manager.scrapers.airfrance_scraper import AirFranceScraper
from scraper_manager.config import CONFIG

async def test():
    scraper = AirFranceScraper(CONFIG)
    scraper.batch_size = 2 # Small batch for testing
    scraper.max_jobs = 5
    scraper.headless = True
    
    print("Testing Air France Scraper...")
    jobs = await scraper.fetch_jobs()
    print(f"\nExtracted {len(jobs)} jobs")
    for job in jobs[:5]:
        print(f"- {job['title']} ({job['location']})")
        print(f"  URL: {job['url']}")
        print(f"  Desc: {len(job.get('description', ''))} chars")

if __name__ == "__main__":
    asyncio.run(test())
