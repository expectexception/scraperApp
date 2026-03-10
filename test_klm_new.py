import asyncio
from playwright.async_api import async_playwright
import bs4

async def main():
    url = "https://careers.klm.com/en/jobs/?page=1"
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-http2', '--disable-blink-features=AutomationControlled']
        )
        # Use stealth args
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        print(f"Loading {url}...")
        try:
            # Disable http2 if needed like I did in the scraper
            # but let's try standard first with a good UA
            await page.goto(url, wait_until='networkidle', timeout=60000)
            await page.wait_for_timeout(5000) # Wait for animation
            
            # Take screenshot
            await page.screenshot(path="/home/rajat/.gemini/antigravity/brain/a1d52894-5c28-497f-8a62-1eb517f7fada/klm_page_1.png", full_page=True)
            
            content = await page.content()
            soup = bs4.BeautifulSoup(content, 'html.parser')
            
            # Look for job links
            # Based on previous failure, it might be in an iframe or specific divs
            print("--- Analyzing links ---")
            links = soup.find_all('a')
            for a in links:
                href = a.get('href', '')
                text = a.get_text(strip=True)
                if href and '/job/' in href:
                    print(f"Found Job Link: {text} -> {href}")
            
            # Look for job cards
            print("--- Analyzing potential job cards ---")
            # Common patterns for job cards
            for div in soup.find_all(['div', 'li', 'article']):
                classes = div.get('class', [])
                if any('job' in c.lower() for c in (classes if isinstance(classes, list) else [classes])):
                    # Print first few to see structure
                    text = div.get_text(strip=True)
                    if len(text) > 10 and len(text) < 200:
                        print(f"Potential Job Card [{div.name}]: {text[:100]}...")
                        
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
