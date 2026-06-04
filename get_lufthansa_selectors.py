import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://apply.lufthansagroup.careers/index.php?ac=search_result&search_criterion_channel%5B%5D=12&language=2")
        await page.wait_for_timeout(5000)
        content = await page.content()
        with open("lufthansa_test.html", "w") as f:
            f.write(content)
        await browser.close()
        
asyncio.run(main())
