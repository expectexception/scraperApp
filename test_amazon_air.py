import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        url = "https://amazon.jobs/content/en/teams/transportation-shipping-logistics/air#jobs-search"
        print(f"Loading {url}...")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)
        
        # Grab job cards
        cards = await page.evaluate('''() => {
            let cardElements = Array.from(document.querySelectorAll("div[class*='job-card-module_root']"));
            return cardElements.map(card => ({
                lines: card.innerText.split('\\n').map(l => l.trim()).filter(l => l)
            }));
        }''')
        
        print("Total job cards found:", len(cards))
        for idx, c in enumerate(cards[:5]):
            print(f"\nCard {idx+1} lines:")
            for line_idx, line in enumerate(c["lines"]):
                print(f"  [{line_idx}] {repr(line)}")
            
        await browser.close()

asyncio.run(main())
