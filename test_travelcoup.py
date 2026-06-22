import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        url = "https://www.travelcoup.com/captain-embraer-145"
        await page.goto(url, wait_until="networkidle", timeout=60000)
        
        body = await page.locator("body").inner_text()
        
        # Clean text
        desc = body
        if "Login" in desc:
            # We want to take content after the top login menu/header
            # Let's see: header has "Login", so we split on "Login\n"
            parts = desc.split("Login\n")
            if len(parts) > 1:
                # The actual job title usually follows, e.g. "Kapitän Embraer 145..."
                desc = parts[1]
                
        # Now clean the bottom
        for marker in ["✕", "Login\nKunden Login", "TRAVELCOUP", "Über uns"]:
            if marker in desc:
                desc = desc.split(marker)[0]
                
        desc = desc.strip()
        print("Cleaned Description:")
        print("=========================")
        print(desc)
        print("=========================")
        await browser.close()

asyncio.run(main())
