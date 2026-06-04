import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        responses = []
        page.on("response", lambda response: responses.append(response.url))
        
        await page.goto("https://www.jobs-ups.com/search-jobs")
        await page.wait_for_timeout(10000)
        
        with open("ups_network.txt", "w") as f:
            for url in responses:
                f.write(url + "\n")
        await browser.close()
        
asyncio.run(main())
