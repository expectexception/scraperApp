import asyncio
from scraper_manager.core import load_scrapers

async def run():
    scrapers = load_scrapers(sites=["menzies"])
    if scrapers:
        print(f"Loaded scraper: {scrapers[0].company_name}")
        scrapers[0].max_jobs = 3
        jobs = await scrapers[0].run()
        print(f"Scraped {len(jobs)} jobs via framework.")
    else:
        print("Failed to load Menzies scraper.")

asyncio.run(run())
