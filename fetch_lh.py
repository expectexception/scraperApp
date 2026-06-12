import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        # capture requests
        urls = []
        page.on("request", lambda request: urls.append(request.url))
        await page.goto("https://apply.lufthansagroup.careers/index.php?ac=search_result&search_criterion_channel%5B%5D=12&language=2", wait_until="networkidle")
        html = await page.content()
        with open("lh_rendered.html", "w") as f:
            f.write(html)
        with open("lh_urls.txt", "w") as f:
            f.write("\n".join(urls))
        await browser.close()

asyncio.run(main())
