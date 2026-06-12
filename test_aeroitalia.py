import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto("https://www.aeroitalia.com/en/company/work-with-us", wait_until="networkidle", timeout=30000)
            html = await page.content()
            with open("aeroitalia_src.html", "w") as f:
                f.write(html)
            print("Saved aeroitalia_src.html")
        except Exception as e:
            print("Exception:", e)
        finally:
            await browser.close()
            
asyncio.run(main())
