import asyncio
import sys
import os
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_service.settings')
import django
django.setup()

from scraper_manager.scrapers.braathens_scraper import BraathensScraper
from scraper_manager.config import CONFIG

async def debug():
    scraper = BraathensScraper(CONFIG)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page, context = await scraper.setup_stealth_page(browser)
        
        await page.goto(scraper.base_url, wait_until='networkidle', timeout=60000)
        
        # Accept cookies
        try:
            await page.click('button#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll', timeout=5000)
            await page.wait_for_timeout(3000)
            print("Clicked cookie accept")
        except Exception as e:
            print("Cookie button not found:", e)
            
        # Scroll down
        await page.evaluate('window.scrollBy(0, 1000)')
        await page.wait_for_timeout(3000)
        await page.screenshot(path='braathens_debug2.png')
        
        # Check frames
        print(f"Frames: {len(page.frames)}")
        for f in page.frames:
            print("Frame name/url:", f.name, f.url)
            
        print(f"Total links with text > 5 chars: {len(links)}")
            
        await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
