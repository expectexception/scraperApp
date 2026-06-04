import asyncio
from scraper_manager.config import CONFIG
from scraper_manager.scrapers import SCRAPERS

async def check_locations():
    new_scrapers = ['maltairport', 'marabu', 'jost', 'faktor', 'challenge', 'flix', 'tradewind']
    
    for name in new_scrapers:
        if name not in SCRAPERS:
            print(f"Scraper {name} not found!")
            continue
            
        print(f"\n--- Checking {name.upper()} ---")
        scraper_cls = SCRAPERS[name]
        
        # Override headless or use filter logic? We just want to see locations
        # Set use_filter to False to see all jobs or keep True to see only matched. Let's keep True for speed but maybe False to see more locations.
        # Let's just fetch jobs and see the first 5 locations
        scraper = scraper_cls(CONFIG)
        scraper.use_filter = False # Don't filter, we just want to see locations
        
        try:
            jobs = await scraper.fetch_jobs()
            print(f"Found {len(jobs)} jobs")
            for job in jobs[:5]:
                print(f"  {job.get('title', 'N/A')} @ {job.get('location', 'N/A')}")
        except Exception as e:
            print(f"Error checking {name}: {e}")

asyncio.run(check_locations())
