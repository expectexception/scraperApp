import asyncio
import os
import django
from pprint import pprint

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_service.settings')
django.setup()

from scraper_manager.scrapers.indigo_scraper import IndiGoScraper
from scraper_manager.config import CONFIG

async def test_api():
    scraper = IndiGoScraper(CONFIG)
    
    # Try the main job search list API
    url = "https://ms-careers-prod.goindigo.in/career-job-list"
    payload = {
        'start': 0,
        'limit': 5,
        'filters': {}
    }
    
    print(f"Testing POST to {url}")
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': 'https://www.goindigo.in/careers/job-search.html?type=&location=&department=',
        'Origin': 'https://www.goindigo.in',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    }
    
    # We can use the scraper's make_request since it has curl_cffi and retry logic
    resp = await scraper.make_request(url, method='POST', json=payload, headers=headers)
    
    if resp and resp.status_code == 200:
        data = resp.json()
        print("Success! Got data:")
        
        # Check if description is in the list API
        if 'jobs' in data:
            for job in data['jobs'][:1]:
                print("\nJob ID:", job.get('jobId'))
                print("Title:", job.get('title'))
                print("Description length:", len(job.get('description', '')))
                if job.get('description'):
                    print("Description snippet:", job['description'][:100])
                    
            print("\nKeys in first job object:", data['jobs'][0].keys())
    else:
        print(f"Failed. Status: {resp.status_code if resp else 'None'}")

if __name__ == "__main__":
    asyncio.run(test_api())
