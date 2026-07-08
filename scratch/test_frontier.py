import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Test FOR1029FREF (Frontier?)
        url = "https://recruiting2.ultipro.com/FOR1029FREF/JobBoard/64ac66bb-52b9-46df-9a34-49db2308f2fe/?q=&o=postedDateDesc"
        print("Navigating to URL...")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        await asyncio.sleep(8)
        
        links = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll("a.opportunity-link")).map(a => ({
                href: a.href,
                text: a.innerText || a.textContent,
                className: a.className
            }));
        }''')
        
        company = await page.evaluate('document.title')
        print(f"Company/Title: {company}")
        print(f"Total links found: {len(links)}")
        if links:
            print(f"First link: {links[0]}")
            
        await context.close()
        await browser.close()

asyncio.run(run())
