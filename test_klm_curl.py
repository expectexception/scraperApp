import asyncio
from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup

async def main():
    url = "https://careers.klm.com/en/jobs/?page=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    print(f"Fetching {url} with curl_cffi...")
    async with AsyncSession(impersonate="chrome110") as s:
        res = await s.get(url, headers=headers)
        print(f"Status: {res.status_code}")
        
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            print("--- Analyzing <a> tags ---")
            links = soup.find_all('a')
            for a in links:
                href = a.get('href', '')
                text = a.get_text(strip=True)
                # Look for links that might be jobs
                if href and ('/job/' in href or '/vacancy/' in href):
                    print(f"Job Link: {text} -> {href}")
            
            # Print first 2000 chars of body to look for patterns
            print("--- Body snippet ---")
            # print(res.text[:2000]) # Too noisy
            # Look for job-title classes
            for tag in soup.find_all(class_=True):
                classes = tag.get('class', [])
                if any('title' in c.lower() or 'job' in c.lower() for c in classes):
                    if len(tag.get_text(strip=True)) > 5 and len(tag.get_text(strip=True)) < 100:
                        print(f"Class match [{tag.name}.{'.'.join(classes)}]: {tag.get_text(strip=True)}")

if __name__ == "__main__":
    asyncio.run(main())
