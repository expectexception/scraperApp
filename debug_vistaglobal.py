import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Use stealth options
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/New_York"
        )
        page = await context.new_page()
        
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            window.chrome = { runtime: {} };
        """)
        
        # Test: with in_iframe=1
        url = "https://hub-vistaglobal.icims.com/jobs/search?ss=1&searchCategory=109470&searchCategory=17882&searchCategory=17912&searchCategory=17886&searchCategory=8748&searchCategory=17898&searchCategory=54473&searchCategory=57874&mobile=false&width=1296&height=500&bga=true&needsRedirect=false&jan1offset=330&jun1offset=330&in_iframe=1"
        print(f"Loading {url}...")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(5000)
            
            body_text = await page.inner_text("body")
            print("Body text length:", len(body_text))
            print("Body text snippet:\n", body_text[:1000])
            
            # Check if jobs are loaded
            jobs = await page.query_selector_all(".iCIMS_JobsTable .row")
            print("Jobs found:", len(jobs))
            
            await page.screenshot(path="vistaglobal_test_iframe.png")
            print("Screenshot saved to vistaglobal_test_iframe.png")
        except Exception as e:
            print("Failed:", e)
            
        await browser.close()

asyncio.run(main())
