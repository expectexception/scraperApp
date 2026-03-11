import asyncio
from scraper_manager.scrapers.brusselsairlines_scraper import BrusselsAirlinesScraper
import logging

logging.basicConfig(level=logging.INFO)

async def test():
    config = {
        'scraper_settings': {
            'use_filter': False,
        },
        'sites': {
            'brusselsairlines': {}
        },
        'scrapers': {
            'brusselsairlines': {
                'headless': True,
                'max_jobs': 20
            }
        }
    }
    
    scraper = BrusselsAirlinesScraper(config)
    jobs = await scraper.fetch_jobs()
    print("Found jobs:")
    for j in jobs:
        print(f"- {j.get('title')}")

if __name__ == "__main__":
    asyncio.run(test())
