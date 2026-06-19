import asyncio
import logging
from scraper_manager.scrapers.westjet_scraper import WestJetScraper

logging.basicConfig(level=logging.INFO)

async def main():
    config = {
        "scraper_settings": {"max_jobs": 5},
        "sites": {
            "westjet": {
                "base_url": "https://jobs.dayforcehcm.com/en-CA/WestJet",
                "jobs_url": "https://jobs.dayforcehcm.com/en-CA/WestJet/OPSCONTROLCENTRE",
                "name": "WestJet"
            }
        }
    }
    scraper = WestJetScraper(config, db_manager=None)
    jobs = await scraper.fetch_jobs()
    print(f"Found {len(jobs)} jobs")
    for j in jobs[:3]:
        print(f"- {j.get('title')} | {j.get('location')}")

if __name__ == "__main__":
    asyncio.run(main())
