import asyncio
import sys
import logging
from scraper_manager.scrapers import SCRAPERS

# Configure logging to show info messages
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

async def test_scrapers():
    keys_to_test = [
        "aaregional",
        "transairhawaii",
        "chevron",
        "virgingalactic",
        "gmr",
        "magnificaair",
        "qantas",
        "alaska",
        "gridiron",
        "flyairshare",
        "adp_fbb94cb3",
        "mountain_air_cargo",
        "skywest",
        "endeavor",
        "ameriflight",
        "nationalairlines",
        "maersk",
        "marabu"
    ]

    config = {
        "scraper_settings": {
            "use_headless": True,
            "max_jobs_per_scraper": 5
        },
        "sites": {k: {"enabled": True} for k in keys_to_test}
    }

    print("=" * 60)
    print("STARTING BATCH SCRAPER VERIFICATION")
    print("=" * 60)

    for key in keys_to_test:
        if key not in SCRAPERS:
            print(f"ERROR: Scraper key '{key}' not found in SCRAPERS dict.")
            continue

        print(f"\n---> Testing scraper: {key} <---")
        try:
            scraper_cls = SCRAPERS[key]
            scraper = scraper_cls(config)
            
            # Run the scraper
            jobs = await scraper.run()
            print(f"[{key}] Result: {len(jobs)} jobs ingested and passed filters.")
            
            # Analyze jobs
            for idx, job in enumerate(jobs[:3]):
                print(f"  Job #{idx+1}:")
                print(f"    Title: {job.get('title')}")
                print(f"    Company: {job.get('company')}")
                print(f"    Location: {job.get('location')}")
                print(f"    URL: {job.get('url')}")
                print(f"    Job ID: {job.get('job_id')}")
                desc = job.get('description', '')
                print(f"    Description length: {len(desc)} characters")
                
                # Check for missing details
                missing = []
                if not job.get('title'): missing.append('title')
                if not job.get('company'): missing.append('company')
                if not job.get('location') or job.get('location') == 'Unknown': missing.append('location')
                if not job.get('url'): missing.append('url')
                if not job.get('job_id'): missing.append('job_id')
                if not desc: missing.append('description')
                
                if missing:
                    print(f"    WARNING: Missing fields: {missing}")
                else:
                    print(f"    STATUS: OK")

        except Exception as e:
            print(f"[{key}] FAILED with exception: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_scrapers())
