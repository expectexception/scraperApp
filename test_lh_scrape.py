import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto("https://apply.lufthansagroup.careers/index.php?ac=search_result&search_criterion_channel%5B%5D=12&language=2", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(5000)
            html = await page.content()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            jobs = soup.select('a')
            print(f"Total links: {len(jobs)}")
            print([j.text.strip() for j in jobs if 'job' in j.get('href', '').lower()][:10])
        except Exception as e:
            print("Exception:", e)
        finally:
            await browser.close()
            
asyncio.run(main())
