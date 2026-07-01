import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        # Launching with --disable-http2 flag
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-http2"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()
        try:
            url = "https://careers.qantas.com/jobs/jobs-in-operations-safety/?per_page=10"
            print("Navigating to Qantas...")
            await page.goto(url, wait_until="networkidle", timeout=60000)
            print("Successfully loaded page!")
            title = await page.title()
            print("Title:", title)
            
            # Print page content length
            content = await page.content()
            print("Length:", len(content))
            
            # Print card classes or elements to check if jobs loaded
            cards = await page.query_selector_all(".card, [class*='card'], [class*='job']")
            print(f"Found {len(cards)} elements with card/job class")
            for c in cards[:5]:
                text = await c.inner_text()
                print("  Element text:", text.strip()[:100])
        except Exception as e:
            print("Failed:", e)
        await browser.close()

asyncio.run(main())
