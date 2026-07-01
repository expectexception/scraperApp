import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()
        try:
            url = "https://careers.qantas.com/jobs/jobs-in-operations-safety/?per_page=10"
            print("Navigating to Qantas...")
            # Go to page waiting for domcontentloaded
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            print("Page loaded (DOM content loaded). Waiting for jobs selector...")
            
            # Wait for the job card links to appear
            try:
                await page.wait_for_selector("a.afp-btn-view-job", timeout=20000)
                print("Selector found!")
            except Exception as e:
                print("Selector wait failed/timed out:", e)
                
            # Print page content length
            content = await page.content()
            print("Length:", len(content))
            
            # Extract jobs
            cards = await page.query_selector_all("a.afp-btn-view-job")
            print(f"Found {len(cards)} view-job links")
            for c in cards[:5]:
                href = await c.get_attribute("href")
                label = await c.get_attribute("aria-label")
                text = await c.inner_text()
                print(f"  Job: text='{text}', href='{href}', label='{label}'")
        except Exception as e:
            print("Failed:", e)
        await browser.close()

asyncio.run(main())
