import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # intercept responses
        responses = []
        page.on("response", lambda r: responses.append(r.url))
        
        await page.goto("https://starlinkaviation.com/careers/job-openings/", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        
        # Check iframes
        frames = page.frames
        print(f"Frames: {[f.url for f in frames]}")
        
        # Check specific API endpoints
        print("API Responses:")
        for r in responses:
            if "api" in r.lower() or "json" in r.lower() or "job" in r.lower():
                print(r)
                
        # print some of the HTML to see where jobs are
        html = await page.content()
        with open("starlink_debug.html", "w") as f:
            f.write(html)
        
        await browser.close()

asyncio.run(main())
