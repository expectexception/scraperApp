import asyncio
from playwright.async_api import async_playwright
import bs4

async def get_dom(url, name):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        print(f"Loading {name}...")
        await page.goto(url, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(3000)
        content = await page.content()
        soup = bs4.BeautifulSoup(content, 'html.parser')
        links = soup.find_all('a')
        print(f"--- {name} ({url}) ---")
        cnt = 0
        for a in links:
            href = a.get('href', '')
            text = a.get_text(strip=True)
            if href and len(text) > 3 and ('/' in href or '#' in href):
                print(f"[{a.get('class', [''])[0] if isinstance(a.get('class'), list) else 'none'}] {text} -> {href}")
                cnt += 1
                if cnt > 15: break
        await browser.close()

async def main():
    await get_dom("https://career.ita-airways.com/search/?q=&sortColumn=referencedate&sortDirection=desc", "ITA")
    await get_dom("https://careers.klm.com/en/jobs/", "KLM")

asyncio.run(main())
