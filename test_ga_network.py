import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        async def handle_resp(resp):
            try:
                if resp.status == 200:
                    content = await resp.text()
                    if "job" in content.lower() or "career" in content.lower():
                        print(f"RESP: {resp.url} (size {len(content)})")
            except Exception:
                pass
                
        page.on("response", handle_resp)
        try:
            await page.goto("https://www.globeair.com/career", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(10000)
        except Exception as e:
            print("Exception:", e)
        finally:
            await browser.close()
            
asyncio.run(main())
