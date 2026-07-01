import asyncio
import sys
from playwright.async_api import async_playwright

urls = {
    "quikjet": "https://quikjet.co.in/careers/",
    "indiaone": "https://www.indiaoneair.com/careers/",
    "qantas": "https://careers.qantas.com/jobs/jobs-in-operations-safety/?per_page=10",
    "chevron": "https://careers.chevron.com/category/aviation-jobs/35016/8307184/1",
    "transair": "https://transairhawaii.com/category/jobs/",
    "aaregional": "https://aaregional.wd503.myworkdayjobs.com/search",
    "magnifica": "https://magnificaair.com/careers/",
    "upmc": "https://careers.upmc.com/job-search-results/?category[]=Other",
    "gmr": "https://careers.gmr.net/gmr/jobs",
    "virgingalactic": "https://vgcareers.virgingalactic.com/global/en/search-results"
}

async def inspect_url(name, url):
    print(f"\n--- Inspecting {name}: {url} ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"[{name}] goto failed, trying domcontentloaded: {e}")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e2:
                print(f"[{name}] goto failed completely: {e2}")
                await browser.close()
                return

        await page.wait_for_timeout(3000)
        title = await page.title()
        content = await page.content()
        print(f"[{name}] Title: {title}")
        print(f"[{name}] Content length: {len(content)}")
        
        # Take a screenshot to inspect visually if needed (can name it after the site)
        screenshot_path = f"inspect_{name}.png"
        await page.screenshot(path=screenshot_path)
        print(f"[{name}] Saved screenshot to {screenshot_path}")

        # Basic selector checks
        # 1. Check for links
        links = await page.query_selector_all("a")
        print(f"[{name}] Found {len(links)} links")
        
        # Print first few link texts and hrefs
        count = 0
        for link in links:
            href = await link.get_attribute("href")
            text = (await link.inner_text()).strip()
            if href and text:
                print(f"  Link: {text[:50]} -> {href[:100]}")
                count += 1
                if count >= 10:
                    break
        
        # 2. Check for button / text presence
        # Let's inspect some specific structures:
        # Workday has workday-specific selectors
        # Phenom has phenom-specific selectors
    
        await browser.close()

async def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    if target in urls:
        await inspect_url(target, urls[target])
    else:
        for name, url in urls.items():
            await inspect_url(name, url)

if __name__ == "__main__":
    asyncio.run(main())
