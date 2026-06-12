import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto("https://jobs.eurocontrol.int/eurocontrol-vacancies/?date=all&keywords=&sort=alphabetical", wait_until="networkidle", timeout=30000)
            print("Loaded Eurocontrol")
            html = await page.content()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            jobs = soup.select('div.vacancy-list-item, div.vacancy, a[href*="vacancy"]')
            print(f"Total jobs: {len(jobs)}")
            if jobs:
                print(jobs[0].text.strip()[:100])
        except Exception as e:
            print("Exception:", e)
        finally:
            await browser.close()
            
asyncio.run(main())
