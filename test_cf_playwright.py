import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        print("Navigating to Egyptair...")
        try:
            await page.goto("https://www.egyptair.com/en/about-egyptair/Pages/careers.aspx", wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"Goto error: {e}")
            
        print("Waiting for Cloudflare...")
        await page.wait_for_timeout(5000)
        
        frames = page.frames
        print(f"Total frames: {len(frames)}")
        for f in frames:
            url = f.url
            if 'cloudflare' in url or 'turnstile' in url:
                print(f"Found CF frame: {url}")
                try:
                    # Click the frame element directly
                    frame_el = await f.frame_element()
                    if await frame_el.is_visible():
                        print("Frame visible! Clicking its center...")
                        box = await frame_el.bounding_box()
                        if box:
                            await page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                            await page.mouse.down()
                            await page.wait_for_timeout(100)
                            await page.mouse.up()
                            print("Clicked frame center!")
                    else:
                        print("Frame not visible.")
                except Exception as e:
                    print(f"Error checking frame: {e}")
                    
        print("Waiting 10s to see if it passes...")
        await page.wait_for_timeout(10000)
        print("Final URL:", page.url)
        print("Final Title:", await page.title())
        await browser.close()

asyncio.run(run())
