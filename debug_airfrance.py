import asyncio
import os
import django
from playwright.async_api import async_playwright

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_service.settings')
django.setup()

from scraper_manager.scrapers.airfrance_scraper import AirFranceScraper
from scraper_manager.config import CONFIG

async def debug():
    scraper = AirFranceScraper(CONFIG)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page, context = await scraper.setup_stealth_page(browser)
        
        url = "https://recrutement.airfrance.com/accueil.aspx?LCID=2057"
        print(f"Navigating to {url}")
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            print("Page loaded (domcontentloaded)")
            await asyncio.sleep(5)
            await page.screenshot(path='airfrance_debug.png')
            html = await page.content()
            with open('airfrance_html.txt', 'w') as f:
                f.write(html)
            print("Screenshot and HTML saved")
        except Exception as e:
            print(f"Error: {e}")
            await page.screenshot(path='airfrance_error.png')
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
