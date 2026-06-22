import asyncio
from scraper_manager.scrapers.k5_aviation_scraper import K5AviationScraper
from scraper_manager.scrapers.jet2_scraper import Jet2Scraper
from scraper_manager.scrapers.dea_scraper import DeaScraper
from scraper_manager.scrapers.skyexpress_scraper import SkyExpressScraper

async def run_tests():
    # Setup dummy config
    config = {
        "scraper_settings": {
            "use_headless": True,
            "max_jobs_per_scraper": 5
        },
        "sites": {
            "k5aviation": {"enabled": True},
            "jet2": {"enabled": True},
            "dea": {"enabled": True},
            "skyexpress": {"enabled": True}
        }
    }

    scrapers = [
        #K5AviationScraper(config),
        Jet2Scraper(config),
        #DeaScraper(config),
        #SkyExpressScraper(config)
    ]
    
    for s in scrapers:
        print(f"Testing {s.site_key}...")
        jobs = await s.fetch_jobs()
        print(f"{s.site_key} fetched {len(jobs)} jobs:")
        for j in jobs[:2]:
            print(j['title'], j['url'])

asyncio.run(run_tests())
