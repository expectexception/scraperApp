import asyncio
from scraper_manager.scrapers.brusselsairlines_scraper import BrusselsAirlinesScraper
from scraper_manager.filter_manager import JobFilterManager

async def test():
    config = {
        'scraper_settings': {
            'use_filter': True,
            'filter_file': 'filter_title.json'
        },
        'sites': {
            'brusselsairlines': {}
        },
        'scrapers': {
            'brusselsairlines': {
                'headless': True
            }
        }
    }
    
    scraper = BrusselsAirlinesScraper(config)
    jobs = await scraper.fetch_jobs()
    print(jobs)

if __name__ == "__main__":
    asyncio.run(test())
