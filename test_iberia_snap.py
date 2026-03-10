import asyncio
from playwright.async_api import async_playwright

async def main():
    sites = {
        "iberia": "https://trabajaconnosotros.iberia.es/",
        "iberiaexpress": "https://portalempleo.iberiaexpress.com/",
        "itaairways": "https://career.ita-airways.com/"
    }
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        for name, url in sites.items():
            page = await context.new_page()
            print(f"Loading {name}: {url}...")
            try:
                await page.goto(url, wait_until='networkidle', timeout=60000)
                await page.wait_for_timeout(5000)
                path = f"/home/rajat/.gemini/antigravity/brain/a1d52894-5c28-497f-8a62-1eb517f7fada/snap_{name}.png"
                await page.screenshot(path=path)
                print(f"Saved {path}")
                
                # Check for links
                links = await page.query_selector_all('a')
                print(f"[{name}] Total <a> tags: {len(links)}")
                # Sample some links
                for l in links[:10]:
                    print(f"  {await l.inner_text()} -> {await l.get_attribute('href')}")
            except Exception as e:
                print(f"Error {name}: {e}")
            finally:
                await page.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
