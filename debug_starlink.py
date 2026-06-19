import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://starlinkaviation.com/careers/job-openings/")
        links = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll("a")).map(a => ({
                href: a.href,
                text: a.innerText || a.textContent
            }));
        }''')
        for link in links:
            href = link.get('href', '').lower()
            text = link.get('text', '').strip()
            if "starlink" in href and "job" in href:
                print(f"HREF: {href} | TEXT: {text}")
        await browser.close()

asyncio.run(main())
