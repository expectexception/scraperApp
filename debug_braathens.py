import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_service.settings')
import django
django.setup()

from scraper_manager.scrapers.braathens_scraper import BraathensScraper
from scraper_manager.config import CONFIG

async def debug():
    scraper = BraathensScraper(CONFIG)
    jobs = await scraper.fetch_jobs()
    print('Jobs found:', len(jobs))
    for j in jobs:
        print(j['title'], '-', j['url'])

if __name__ == "__main__":
    asyncio.run(debug())
