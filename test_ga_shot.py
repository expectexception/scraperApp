import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.globeair.com/career#openpositions", wait_until="networkidle", timeout=30000)
        await page.screenshot(path="globeair.png", full_page=True)
        await browser.close()
        
asyncio.run(main())
