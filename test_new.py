import asyncio
import logging
from scraper_manager.scrapers.starlinkaviation_scraper import StarlinkAviationScraper
from scraper_manager.scrapers.sunairjets_scraper import SunAirJetsScraper
from scraper_manager.scrapers.aircanada_scraper import AirCanadaScraper
from scraper_manager.scrapers.dhl_scraper import DHLScraper
from scraper_manager.scrapers.jet_aviation_scraper import JetAviationScraper
from scraper_manager.scrapers.westjet_scraper import WestJetScraper

logging.basicConfig(level=logging.INFO)

async def run_scraper(scraper_class, name, site_key=None):
    print(f"\n--- Testing {name} ---")
    config = {
        "scraper_settings": {"max_jobs": 5},
        "sites": {
            "starlinkaviation": {"jobs_url": "https://starlinkaviation.com/careers/job-openings/"},
            "sunairjets": {"jobs_url": "https://www.sunairjets.com/careers/"},
            "air_canada": {"jobs_url": "https://careers.aircanada.com/ca/en"},
            "dhl": {"jobs_url": "https://careers.dhl.com/global/en/c/operations-jobs"},
            "jet_aviation": {"jobs_url": "https://jobs.jetaviation.com/go/Europe/8766702/"},
            "westjet": {"jobs_url": "https://jobs.dayforcehcm.com/en-CA/WestJet/OPSCONTROLCENTRE", "name": "WestJet"}
        }
    }
    
    # westjet_scraper has a different signature but inherits from DayforceScraper
    # DayforceScraper takes site_key in init. Let's just pass config
    if site_key:
        scraper = scraper_class(config, db_manager=None, site_key=site_key)
    else:
        scraper = scraper_class(config, db_manager=None)
        
    jobs = await scraper.fetch_jobs()
    print(f"Found {len(jobs)} jobs (first phase)")
    for j in jobs[:3]:
        print(f"- {j.get('title', 'Unknown')} | {j.get('location', 'Unknown')}")

async def main():
    await run_scraper(StarlinkAviationScraper, "Starlink Aviation")
    await run_scraper(SunAirJetsScraper, "Sun Air Jets")
    await run_scraper(AirCanadaScraper, "Air Canada")
    await run_scraper(DHLScraper, "DHL")
    await run_scraper(JetAviationScraper, "Jet Aviation")
    await run_scraper(WestJetScraper, "WestJet")

if __name__ == "__main__":
    asyncio.run(main())
