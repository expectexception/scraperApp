import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://www.jobs-ups.com/search-jobs")
        await page.wait_for_timeout(5000)
        content = await page.content()
        with open("ups_test.html", "w") as f:
            f.write(content)
        await browser.close()
        
asyncio.run(main())
