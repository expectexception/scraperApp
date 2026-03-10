import asyncio
import logging
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        print("Loading https://airdolomiti.altamiraweb.com/default")
        await page.goto("https://airdolomiti.altamiraweb.com/default")
        await page.wait_for_timeout(5000)
        
        await page.screenshot(path="airdolomiti_debug.png")
        html = await page.content()
        with open("airdolomiti_html.txt", "w") as f:
            f.write(html)
            
        links = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('a.GRID_DAT_COMMAND')).map(a => ({t: a.innerText.trim(), h: a.href}));
        }''')
        print(f"Found links: {links}")
        await browser.close()

asyncio.run(main())
