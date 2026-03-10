import asyncio
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_service.settings')
django.setup()

from scraper_manager.scrapers.finnair_scraper import FinnairScraper
from scraper_manager.config import CONFIG

async def debug():
    scraper = FinnairScraper(CONFIG)
    
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page, context = await scraper.setup_stealth_page(browser)
        
        print("Navigating to:", scraper.base_url)
        try:
            await page.goto(scraper.base_url, wait_until='networkidle', timeout=30000)
            print("Loaded successfully")
        except Exception as e:
            print("Failed to load:", e)
            
        html = await page.inner_html('body')
        with open('finnair_html.txt', 'w') as f:
            f.write(html)
            
        await page.screenshot(path='finnair_debug.png')
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
