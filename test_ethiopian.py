import asyncio
from scraper_manager.scrapers.base_scraper import BaseScraper
from bs4 import BeautifulSoup

class DummyScraper(BaseScraper):
    def __init__(self):
        super().__init__({'sites': {'ethiopian': {}}, 'scraper_settings': {}}, 'ethiopian')

async def main():
    s = DummyScraper()
    res = await s.make_request("https://corporate.ethiopianairlines.com/AboutEthiopian/careers/vacancies")
    print("Status:", res.status_code)
    # Print exactly which links are on the page to see if there's any.
    soup = BeautifulSoup(res.text, 'html.parser')
    for a in soup.find_all('a'):
        href = a.get('href', '')
        if 'application' in href.lower() or 'docs' in href.lower():
            print("FOUND DOC:", href)
    
asyncio.run(main())
