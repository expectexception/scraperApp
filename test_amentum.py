import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Navigating...")
        await page.goto("https://www.amentumcareers.com/jobs/search?query=")
        await page.wait_for_timeout(5000)
        jobs = await page.locator("div.job").count()
        print(f"Job elements: {jobs}")
        if jobs == 0:
            jobs2 = await page.locator(".job-listing").count()
            print(f"job-listing elements: {jobs2}")
            jobs3 = await page.locator("a[href*='/jobs/']").count()
            print(f"a[href*='/jobs/'] elements: {jobs3}")
            jobs4 = await page.locator(".job-title").count()
            print(f"job-title elements: {jobs4}")
        
        content = await page.content()
        with open("amentum.html", "w") as f:
            f.write(content)
        await browser.close()

asyncio.run(run())
