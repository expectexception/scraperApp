import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        print("Loading El Al careers...")
        try:
            await page.goto("https://www.elal.com/eng/about/careers", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)
            links = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a'))
                    .map(a => ({t: a.innerText.trim(), h: a.href}))
            }''')
            for l in links: print(f"Title: {l['t']} | URL: {l['h']}")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

asyncio.run(main())
