import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        print("Loading https://dat.dk/corporate/careers")
        await page.goto("https://dat.dk/corporate/careers", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        
        links = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('a'))
                .map(a => ({t: a.innerText.trim(), h: a.href}))
        }''')
        
        for l in links:
            if l['t'] and l['h']:
                print(f"Title: {l['t']} | URL: {l['h']}")
        await browser.close()

asyncio.run(main())
