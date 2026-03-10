import asyncio
from playwright.async_api import async_playwright

async def main():
    url = "https://www.jsfirm.com"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Use a real UA
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        print(f"Loading {url}...")
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(5000)
            
            # Take screenshot of home
            await page.screenshot(path="/home/rajat/.gemini/antigravity/brain/a1d52894-5c28-497f-8a62-1eb517f7fada/jsfirm_home.png")
            
            # Check for input and button
            # loc_input = '#ctl00_ctl00_ucQuickJobSearch_txtWhere_Input'
            # search_btn = '#ucQuickJobSearch_btnSearchJobs'
            
            input_exists = await page.query_selector('#ctl00_ctl00_ucQuickJobSearch_txtWhere_Input')
            btn_exists = await page.query_selector('#ucQuickJobSearch_btnSearchJobs')
            
            print(f"Input exists: {bool(input_exists)}")
            print(f"Button exists: {bool(btn_exists)}")
            
            if input_exists and btn_exists:
                 print("Filling Florida and clicking search...")
                 await page.fill('#ctl00_ctl00_ucQuickJobSearch_txtWhere_Input', 'Florida')
                 await page.click('#ucQuickJobSearch_btnSearchJobs')
                 await page.wait_for_timeout(10000)
                 await page.screenshot(path="/home/rajat/.gemini/antigravity/brain/a1d52894-5c28-497f-8a62-1eb517f7fada/jsfirm_results.png")
                 
                 # Check for welljob divs
                 cards = await page.query_selector_all('div.welljob')
                 print(f"Found {len(cards)} job cards.")
            else:
                # Find any inputs or buttons that look like search
                print("--- Searching for alternative selectors ---")
                inputs = await page.query_selector_all('input')
                for i in inputs:
                    print(f"Input: id={await i.get_attribute('id')}, name={await i.get_attribute('name')}")
                
                btns = await page.query_selector_all('button, input[type="button"], input[type="submit"]')
                for b in btns:
                    print(f"Button: id={await b.get_attribute('id')}, value={await b.get_attribute('value')}")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
