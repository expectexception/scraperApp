import asyncio
from playwright.async_api import async_playwright

async def main():
    url = "https://careers.klm.com/en/jobs/?page=1"
    async with async_playwright() as p:
        # headful might help bypass some bot detection if it's behavioral
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-http2', '--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Listen for all requests
        async def handle_request(request):
            if any(x in request.url.lower() for x in ['api', 'job', 'search', 'vacancy', 'graphql']):
                print(f"Request: {request.method} {request.url}")

        async def handle_response(response):
             if any(x in response.url.lower() for x in ['api', 'job', 'search', 'vacancy', 'graphql']):
                print(f"Response: {response.status} {response.url}")
                if 'json' in response.headers.get('content-type', '').lower():
                    try:
                        # data = await response.json()
                        # print(f"JSON Data detected from {response.url}")
                        pass
                    except:
                        pass

        page.on("request", handle_request)
        page.on("response", handle_response)

        print(f"Navigating to {url}...")
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(10000) # Wait for content to load
            await page.screenshot(path="/home/rajat/.gemini/antigravity/brain/a1d52894-5c28-497f-8a62-1eb517f7fada/klm_network_debug.png")
            
            # Try to click 'Accept' if cookie banner
            try:
                await page.click('button:has-text("Accept")', timeout=5000)
                await page.wait_for_timeout(2000)
            except:
                pass

        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
