import asyncio
import logging
from scraper_manager.scrapers.flexjet_scraper import FlexjetScraper
from scraper_manager.scrapers.cae_scraper import CAEScraper
from scraper_manager.scrapers.rtx_scraper import RtxScraper
from scraper_manager.scrapers.jpmc_scraper import JpmcScraper
from scraper_manager.scrapers.moncton_adp_scraper import MonctonAdpScraper

logging.basicConfig(level=logging.INFO)

async def run_scraper(scraper_class, name):
    print(f"\n--- Testing {name} ---")
    config = {
        "scraper_settings": {"max_jobs": 5},
        "sites": {
            "flexjet": {"jobs_url": "https://careers.flexjet.com/us/en/c/corporate-operations-and-owner-support-jobs", "base_url": "https://careers.flexjet.com"},
            "cae": {"base_url": "https://cae.wd3.myworkdayjobs.com/en-US/career/", "jobs_url": "https://cae.wd3.myworkdayjobs.com/wday/cxs/cae/career/jobs"},
            "rtx": {"base_url": "https://careers.rtx.com", "jobs_url": "https://careers.rtx.com/global/en/search-results"},
            "jpmc": {"base_url": "https://jpmc.fa.oraclecloud.com", "jobs_url": "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/jobs", "api_url": "https://jpmc.fa.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions", "site_number": "CX_1001"},
            "moncton_adp": {"jobs_url": "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid=06351502-0666-4c6f-9a0b-165c5faeab35&ccId=9200784035909_2&lang=en_CA", "base_url": "https://workforcenow.adp.com"}
        }
    }
    scraper = scraper_class(config, db_manager=None)
    jobs = await scraper.fetch_jobs()
    print(f"Found {len(jobs)} jobs (first phase)")
    for j in jobs[:3]:
        print(f"- {j.get('title', 'Unknown')} | {j.get('location', 'Unknown')}")

async def main():
    await run_scraper(FlexjetScraper, "Flexjet")
    await run_scraper(CAEScraper, "CAE")
    await run_scraper(RtxScraper, "RTX")
    await run_scraper(JpmcScraper, "JPMorgan Chase")
    await run_scraper(MonctonAdpScraper, "Moncton ADP")

if __name__ == "__main__":
    asyncio.run(main())
