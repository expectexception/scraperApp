import asyncio
from scraper_manager.scrapers.base_scraper import BaseScraper

class DummyScraper(BaseScraper):
    def __init__(self):
        super().__init__({'sites': {'egyptair': {}}, 'scraper_settings': {}}, 'egyptair')

async def main():
    s = DummyScraper()
    res = await s.make_request("https://www.egyptair.com/en/about-egyptair/Pages/careers.aspx")
    print("Status:", res.status_code)
    print("Cloudflare in page?", "Cloudflare" in res.text)
    print("Title:", res.text.split("<title>")[1].split("</title>")[0] if "<title>" in res.text else "No title")
    
asyncio.run(main())
