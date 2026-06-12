import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        # capture requests
        urls = []
        page.on("request", lambda request: urls.append(request.url))
        await page.goto("https://vistaglobal.com/careers/", wait_until="networkidle")
        html = await page.content()
        with open("vista_rendered.html", "w") as f:
            f.write(html)
        with open("vista_urls.txt", "w") as f:
            f.write("\n".join(urls))
        await browser.close()

asyncio.run(main())
