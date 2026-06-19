import asyncio
import logging
from scraper_manager.scrapers.hyperion_scraper import HyperionScraper
from scraper_manager.scrapers.magma_scraper import MagmaScraper
from scraper_manager.scrapers.maersk_scraper import MaerskScraper

logging.basicConfig(level=logging.INFO)

async def run_scraper(scraper_class, name):
    print(f"\n--- Testing {name} ---")
    config = {
        "scraper_settings": {"max_jobs": 5},
        "sites": {
            "hyperion": {"jobs_url": "https://hyperion.aero/job-openings/", "base_url": "https://hyperion.aero/job-openings/"},
            "magma": {"jobs_url": "https://magma.aero/careers/", "base_url": "https://magma.aero/careers/"},
            "maersk": {"jobs_url": "https://www.maersk.com/careers/vacancies?continent=&category=Air+Freight&country=&searchText=&limit=24", "base_url": "https://www.maersk.com/careers/"}
        }
    }
    scraper = scraper_class(config, db_manager=None)
    jobs = await scraper.fetch_jobs()
    print(f"Found {len(jobs)} jobs (first phase)")
    for j in jobs[:3]:
        print(f"- {j.get('title', 'Unknown')} | {j.get('location', 'Unknown')}")

async def main():
    await run_scraper(HyperionScraper, "Hyperion")
    await run_scraper(MagmaScraper, "Magma")
    await run_scraper(MaerskScraper, "Maersk")

if __name__ == "__main__":
    asyncio.run(main())
