import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        await page.goto("https://www.jobs-ups.com/search-jobs", wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)
        
        await page.screenshot(path="ups_search.png", full_page=True)
        html = await page.content()
        with open("ups_search_2.html", "w") as f:
            f.write(html)
            
        await browser.close()
        
asyncio.run(main())
