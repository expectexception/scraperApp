import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        await page.goto("https://www.sunairjets.com/careers/", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        
        links = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll("a")).map(a => ({
                href: a.href,
                text: a.innerText || a.textContent
            }));
        }''')
        
        print(f"Total links: {len(links)}")
        for link in links:
            href = link.get('href', '').lower()
            text = link.get('text', '').strip()
            if "sunairjets.com" in href and "job" not in href and "career" not in href:
                # just print some to see structure
                pass
            if text and len(text) > 10:
                print(f"HREF: {href} | TEXT: {text}")
        
        await browser.close()

asyncio.run(main())
