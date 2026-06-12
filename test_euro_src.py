import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto("https://jobs.eurocontrol.int/eurocontrol-vacancies/?date=all&keywords=&sort=alphabetical", wait_until="networkidle", timeout=30000)
            html = await page.content()
            with open("euro_src.html", "w") as f:
                f.write(html)
            print("Saved euro_src.html")
        except Exception as e:
            print("Exception:", e)
        finally:
            await browser.close()
            
asyncio.run(main())
