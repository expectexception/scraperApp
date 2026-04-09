import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        try:
            await page.goto("https://ag.wd3.myworkdayjobs.com/Airbus")
            print("Base URL success")
        except Exception as e:
            print("Error base url:", e)
        
        try:
            await page.goto("https://ag.wd3.myworkdayjobs.com/Airbus")
        except Exception as e:
            pass

        await browser.close()

asyncio.run(main())
