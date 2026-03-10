import asyncio
from playwright.async_api import async_playwright

async def check(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        try:
            res = await page.goto(url, wait_until='domcontentloaded', timeout=15000)
            print(f"{url} -> Status: {res.status if res else 'N/A'}")
        except Exception as e:
            print(f"{url} -> Error: {type(e).__name__}")
        finally:
            await browser.close()

async def main():
    urls = [
        "https://empleo.iberia.es/",
        "https://careers.iberia.com/",
        "https://jobs.iberia.com/",
        "https://portalempleo.iberiaexpress.com/"
    ]
    for u in urls:
        await check(u)

asyncio.run(main())
