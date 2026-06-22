import os
import asyncio
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backendMain.settings')
django.setup()

from scraper_manager.scrapers.rtx_scraper import RtxScraper

async def main():
    config = {
        "headless": True,
        "max_jobs": 50,
        "use_filter": True
    }
    scraper = RtxScraper(config)
    jobs = await scraper.fetch_jobs()
    print("Fetched jobs length:", len(jobs))

asyncio.run(main())
