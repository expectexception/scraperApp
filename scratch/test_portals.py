import asyncio
from playwright.async_api import async_playwright
import requests
from bs4 import BeautifulSoup

def test_requests(url):
    print(f"\n--- Testing requests for {url} ---")
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        print(f"Status Code: {r.status_code}")
        print(f"Title: {soup.title.string if soup.title else 'No Title'}")
        
        # Count links
        links = soup.find_all('a')
        print(f"Total links: {len(links)}")
    except Exception as e:
        print(f"Requests failed: {e}")

test_requests("https://www.avincis.com/jobs/italy/")
test_requests("https://careers.velora.ae/search/")
test_requests("https://hris.peoplehum.com/ehire/jobs/greenafrica")
