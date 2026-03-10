import asyncio
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_service.settings')
django.setup()

from scraper_manager.scrapers.braathens_scraper import BraathensScraper
from scraper_manager.config import CONFIG
from scraper_manager.db_manager import DjangoDBManager

async def main():
    db = DjangoDBManager()
    scraper = BraathensScraper(CONFIG, db_manager=db)
    jobs = await scraper.run()
    
    print(f"\nTotal jobs extracted: {len(jobs)}")
    for j in jobs:
        print(f"- {j['title']} ({j['location']})")

if __name__ == "__main__":
    asyncio.run(main())
