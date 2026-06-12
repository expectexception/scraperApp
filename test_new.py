import asyncio
from scraper_manager.scrapers.vistaglobal_scraper import VistaGlobalScraper
from scraper_manager.scrapers.globeair_scraper import GlobeairScraper
from scraper_manager.scrapers.lufthansagroup_scraper import LufthansagroupScraper

async def run_scraper(scraper_class, name):
    print(f"\n--- Testing {name} ---")
    scraper = scraper_class({}, db_manager=None)
    jobs = await scraper.fetch_jobs()
    print(f"Found {len(jobs)} jobs")
    for j in jobs[:3]:
        print(f"- {j['title']} | {j['location']}")

async def main():
    await run_scraper(VistaGlobalScraper, "Vista Global")
    await run_scraper(GlobeairScraper, "GlobeAir")
    await run_scraper(LufthansagroupScraper, "Lufthansa Group")

if __name__ == "__main__":
    asyncio.run(main())
