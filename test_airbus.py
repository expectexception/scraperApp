import asyncio
from scraper_manager.scrapers.airbus_scraper import AirbusScraper
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    s = AirbusScraper({'scrapers': {'airbus': {'search_queries': ['']}}})
    s.max_jobs = 100
    jobs = await s.fetch_jobs()
    print("Jobs fetched:", len(jobs))
    for job in jobs:
        if job['url'].endswith('None') or 'None' in job['url'] or 'None' in job['job_id']:
            print("BAD JOB", job)
    res = await s.fetch_job_descriptions(jobs)
    print("Description fetched:", len(res))

asyncio.run(main())
