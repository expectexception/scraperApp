import asyncio
import logging
from scraper_manager.scrapers.austrianairlines_scraper import AustrianAirlinesScraper

async def test_austrian():
    logging.basicConfig(level=logging.INFO)
    mock_config = {
        'scraper_settings': {
            'batch_size': 1,
            'stealth_mode': True,
            'use_filter': False,
            'impersonate_list': ['chrome110']
        },
        'sites': {
            'austrianairlines': {
                'name': 'Austrian Airlines',
                'base_url': 'https://careers.austrian.com'
            }
        },
        'scrapers': {
            'austrianairlines': {
                'max_jobs': 2,
                'headless': True
            }
        }
    }
    scraper = AustrianAirlinesScraper(mock_config)
    jobs = await scraper.fetch_jobs()
    print(f"Found {len(jobs)} jobs")
    for job in jobs:
        print(f"Title: {job['title']}, URL: {job['url']}")

if __name__ == "__main__":
    asyncio.run(test_austrian())
