import asyncio
import logging
import sys
from scraper_manager.scrapers.hahnair_scraper import HahnAirScraper

async def test_hahnair():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    mock_config = {
        'scraper_settings': {
            'batch_size': 1,
            'stealth_mode': True,
            'use_filter': False,
            'impersonate_list': ['chrome110']
        },
        'sites': {
            'hahnair': {
                'name': 'Hahn Air Lines',
                'base_url': 'https://www.hahnair.com/en/career/career'
            }
        },
        'scrapers': {
            'hahnair': {
                'max_jobs': 2,
                'headless': True
            }
        }
    }
    scraper = HahnAirScraper(mock_config)
    jobs = await scraper.fetch_jobs()
    print(f"Found {len(jobs)} jobs")
    for job in jobs:
        print(f"Title: {job['title']}")
        print(f"Description length: {len(job['description'])}")
        print(f"Description preview: {job['description'][:100]}...")

if __name__ == "__main__":
    asyncio.run(test_hahnair())
