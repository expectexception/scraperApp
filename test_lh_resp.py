import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        async def handle_resp(resp):
            try:
                content = await resp.text()
                if "job" in content.lower() and len(content) > 1000:
                    print(f"RESP: {resp.url} (size {len(content)})")
            except Exception:
                pass
                
        page.on("response", handle_resp)
        try:
            await page.goto("https://apply.lufthansagroup.careers/index.php?ac=search_result&search_criterion_channel%5B%5D=12&language=2", wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_timeout(8000)
        except Exception as e:
            print("Exception:", e)
        finally:
            await browser.close()
            
asyncio.run(main())
