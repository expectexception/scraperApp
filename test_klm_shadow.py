import asyncio
from playwright.async_api import async_playwright

async def main():
    url = "https://careers.klm.com/en/jobs/?page=1"
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-http2', '--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        print(f"Loading {url}...")
        try:
            # wait_until='domcontentloaded' to avoid protocol timeouts on networkidle
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(10000) # Wait for SPA load
            
            # Shadow DOM piercing link extractor
            links = await page.evaluate('''() => {
                const results = [];
                const searchShadow = (root) => {
                    if (!root) return;
                    
                    // Find links in current root
                    const links = root.querySelectorAll('a');
                    links.forEach(a => {
                        results.push({t: (a.innerText || '').trim(), h: a.href});
                    });
                    
                    // Recurse into all children with shadow roots
                    const allElements = root.querySelectorAll('*');
                    allElements.forEach(el => {
                        if (el.shadowRoot) {
                            searchShadow(el.shadowRoot);
                        }
                    });
                };
                
                searchShadow(document);
                return results;
            }''')
            
            import re
            for l in links:
                if l['h'] and (re.search(r'-\d+$', l['h']) or '/job/' in l['h'] or '/vacancy/' in l['h']):
                     print(f"Potential Job: {l['t']} -> {l['h']}")
                elif len(l['t']) > 5:
                     # print(f"Other Link: {l['t']} -> {l['h']}")
                     pass

        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
