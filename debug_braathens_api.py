import asyncio
import sys
import os
from curl_cffi import requests as curl_requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_service.settings')
import django
django.setup()

from scraper_manager.scrapers.braathens_scraper import BraathensScraper
from scraper_manager.config import CONFIG

async def debug():
    scraper = BraathensScraper(CONFIG)
    api_url = "https://recruiter-api.hr-manager.net/jobportal.svc/braathens/positionlist/json/?mediaid=4615&take=20&sortby=Created&sortasc=0"
    
    async with curl_requests.AsyncSession() as session:
        response = await session.get(api_url)
        data = response.json()
        
        jobs = []
        if 'Items' in data:
            for item in data['Items']:
                title = item.get('Name', '')
                item_id = item.get('Id', '')
                url = f"https://www.braathens.com/career/?rmpage=job&rmjob={item_id}"
                print(f"[{item_id}] {title} - {url}")

if __name__ == "__main__":
    asyncio.run(debug())
