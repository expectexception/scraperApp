import asyncio
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_service.settings')
django.setup()

from scraper_manager.scrapers.cathay_scraper import CathayPacificScraper
from scraper_manager.config import CONFIG

async def main():
    scraper = CathayPacificScraper(CONFIG)
    jobs = await scraper.fetch_jobs()
    
    print(f"\nTotal jobs extracted: {len(jobs)}")
    for j in jobs[:5]:
        print(f"- {j.get('title')} ({j.get('location')}) - {j.get('url')}")

if __name__ == "__main__":
    asyncio.run(main())
