import asyncio
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_service.settings')
django.setup()

from scraper_manager.scrapers.indigo_scraper import IndiGoScraper
from scraper_manager.config import CONFIG
from scraper_manager.db_manager import DjangoDBManager

async def debug():
    db = DjangoDBManager()
    scraper = IndiGoScraper(CONFIG, db_manager=db)
    jobs = await scraper.run()
    print(f"Total jobs: {len(jobs)}")
    for j in jobs[:5]:
        print(f"- {j.get('title')}")

if __name__ == "__main__":
    asyncio.run(debug())
