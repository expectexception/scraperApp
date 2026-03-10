import asyncio
import os
import django
from playwright.async_api import async_playwright
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_service.settings')
django.setup()

from scraper_manager.scrapers.austrianairlines_scraper import AustrianAirlinesScraper
from scraper_manager.config import CONFIG

async def debug():
    logging.basicConfig(level=logging.INFO)
    scraper = AustrianAirlinesScraper(CONFIG)
    scraper.headless = True
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page, context = await scraper.setup_stealth_page(browser)
        
        try:
            print(f"Navigating to {scraper.base_url}...")
            await page.goto(scraper.base_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(5000)
            
            # Take screenshot before cookie handling
            await page.screenshot(path="austrian_1_initial.png")
            print("Took screenshot austrian_1_initial.png")
            
            # Handle cookies
            try:
                cookie_btn = page.locator('text=Select all, text=Accept all, text=Zustimmen, id=cmplz-accept-all').first
                if await cookie_btn.is_visible():
                    print("Clicking cookie button")
                    await cookie_btn.click()
                    await page.wait_for_timeout(2000)
            except:
                pass
                
            await page.screenshot(path="austrian_2_after_cookie.png")
            print("Took screenshot austrian_2_after_cookie.png")
            
            # Check for results
            links_count = await page.locator('a.jobad-link-wrapper').count()
            print(f"Found {links_count} job links")
            
            if links_count == 0:
                content = await page.content()
                with open("austrian_debug.html", "w") as f:
                    f.write(content)
                print("Wrote austrian_debug.html")

        except Exception as e:
            print(f"Error: {e}")
            await page.screenshot(path="austrian_error.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
