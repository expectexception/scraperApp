import asyncio
from playwright.async_api import async_playwright

async def snap(url, name):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        try:
            print(f"Snapping {name}: {url}")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(2000)
            await page.screenshot(path=f"/home/rajat/.gemini/antigravity/brain/a1d52894-5c28-497f-8a62-1eb517f7fada/snap_{name}.png", full_page=True)
            print(f"Saved snap_{name}.png")
        except Exception as e:
            print(f"Error for {name}: {e}")
        finally:
            await browser.close()

async def main():
    sites = [
        ("https://www.iberia.com/gb/careers/", "iberia"),
        ("https://iberiaexpress.com/en/general-info/corporate/employment", "iberiaexpress"),
        ("https://www.icelandair.com/about/job-vacancies/", "icelandair"),
        ("https://career.ita-airways.com/", "itaairways"),
        ("https://careers.klm.com/en/jobs/", "klm")
    ]
    for url, name in sites:
        await snap(url, name)

asyncio.run(main())
