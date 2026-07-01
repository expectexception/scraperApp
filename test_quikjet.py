import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Using a full context to bypass 403
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        page = await context.new_page()
        # Add stealth script
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            window.chrome = {
                runtime: {}
            };
        """)
        try:
            await page.goto("https://quikjet.co.in/careers/", wait_until="networkidle", timeout=60000)
            text = await page.inner_text("body")
            print("STATUS: SUCCESS")
            print("LENGTH:", len(text))
            print("TEXT SNIPPET:")
            print(text[:2000])
        except Exception as e:
            print("STATUS: FAILED")
            print("ERROR:", e)
        await browser.close()

asyncio.run(main())
