import asyncio
import logging
import sys
from scraper_manager.scrapers.easyjet_scraper import EasyJetScraper

async def test_easyjet():
    print("Starting EasyJet test...")
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    mock_config = {
        'scraper_settings': {
            'batch_size': 1,
            'stealth_mode': True,
            'use_filter': False,
            'impersonate_list': ['chrome110']
        },
        'sites': {
            'easyjet': {
                'name': 'easyJet',
                'base_url': 'https://careers.easyjet.com/en'
            }
        },
        'scrapers': {
            'easyjet': {
                'max_jobs': 3,
                'headless': True
            }
        }
    }
    try:
        scraper = EasyJetScraper(mock_config)
        print("Scraper initialized, fetching jobs...")
        jobs = await scraper.fetch_jobs()
        print(f"Test finished. Found {len(jobs)} jobs")
        for job in jobs:
            print(f"Title: {job['title']}, Location: {job['location']}, URL: {job['url']}")
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_easyjet())
