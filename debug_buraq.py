import asyncio
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_service.settings')
django.setup()

from scraper_manager.scrapers.buraqair_scraper import BuraqAirScraper
from scraper_manager.config import CONFIG

async def debug():
    scraper = BuraqAirScraper(CONFIG)
    
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page, context = await scraper.setup_stealth_page(browser)
        
        await page.goto(scraper.base_url, wait_until='networkidle', timeout=60000)
        
        html = await page.inner_html('body')
        with open('buraq_html.txt', 'w') as f:
            f.write(html)
            
        links = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('a')).map(a => a.href)
        }''')
        
        print(f"Total links: {len(links)}")
        for l in set(links):
            if 'job' in l.lower() or 'career' in l.lower():
                print("Relevant link:", l)
                
        await page.screenshot(path='buraq_debug.png')
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
