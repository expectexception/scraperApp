import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://jobs.dayforcehcm.com/en-CA/WestJet/OPSCONTROLCENTRE", wait_until="networkidle")
        await page.wait_for_timeout(5000)
        html = await page.content()
        with open("westjet_debug.html", "w") as f:
            f.write(html)
        await browser.close()

asyncio.run(run())
