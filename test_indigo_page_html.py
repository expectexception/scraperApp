import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        # Navigate to one of the job urls we saw in the log
        url = "https://www.goindigo.in/careers/job-search.html?job-id=819717" # using a standard career URL pattern
        print(f"Navigating to {url}")
        await page.goto(url, wait_until='networkidle', timeout=30000)
        await asyncio.sleep(5)
        
        # Take a look at the HTML
        html = await page.content()
        with open('indigo_job_page.html', 'w') as f:
            f.write(html)
        
        # Take a screenshot
        await page.screenshot(path='indigo_job_page.png')
        await browser.close()
        print("Done")

if __name__ == "__main__":
    asyncio.run(main())
