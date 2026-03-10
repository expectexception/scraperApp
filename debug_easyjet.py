import asyncio
from playwright.async_api import async_playwright
import logging

async def debug_easyjet():
    logging.basicConfig(level=logging.INFO)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        try:
            print("Navigating to EasyJet apply-now...")
            await page.goto("https://careers.easyjet.com/en/apply-now", wait_until='networkidle', timeout=60000)
            await page.screenshot(path="easyjet_1_apply_now.png")
            
            # Look for categories
            # The user says "after selecting any catigary"
            categories = await page.locator('.career-area-card, a[href*="career-area"], .category-link').all()
            print(f"Found {len(categories)} categories")
            
            # Let's see what's on the page
            content = await page.content()
            with open("easyjet_apply_now.html", "w") as f:
                f.write(content)
                
            # Try to click a "Search all jobs" or similar if it exists
            search_all = page.locator('text=Search all jobs, text=Find a job, .btn-primary').first
            if await search_all.is_visible():
                print("Clicking search all jobs...")
                await search_all.click()
                await page.wait_for_load_state('networkidle')
                print(f"Redirected to: {page.url}")
                await page.screenshot(path="easyjet_2_after_click.png")
            else:
                # Try clicking a category
                first_cat = page.locator('.career-area-card, a[href*="/en/career-area/"]').first
                if await first_cat.is_visible():
                    print("Clicking first category...")
                    await first_cat.click()
                    await page.wait_for_load_state('networkidle')
                    print(f"After category click: {page.url}")
                    await page.screenshot(path="easyjet_3_category.png")
                    
                    # Look for job search link in category page
                    search_jobs = page.locator('text=Search Jobs, text=Apply Now, [href*="taleo.net"]').first
                    if await search_jobs.is_visible():
                        print("Clicking search jobs in category...")
                        await search_jobs.click()
                        await page.wait_for_load_state('networkidle')
                        print(f"Final URL: {page.url}")
                        await page.screenshot(path="easyjet_4_final.png")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_easyjet())
