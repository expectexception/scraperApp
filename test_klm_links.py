import asyncio
from curl_cffi.requests import AsyncSession
import re
import json

async def main():
    url = "https://careers.klm.com/en/jobs/?page=1"
    async with AsyncSession(impersonate="chrome110") as s:
        res = await s.get(url, timeout=30)
        
        # Look for the jobs data
        # Often it's in a window.__INITIAL_STATE__ or similar
        # Based on previous output, it's inside a push() or similar
        
        # Search for any large JSON-like string
        match = re.search(r'\{"functionality_storage"[\s\S]*?\}', res.text)
        if match:
            try:
                data = json.loads(match.group(0))
                print("Found JSON Data!")
                # print(json.dumps(data, indent=2)[:2000])
            except:
                pass

        # Let's try to find all URLs that match our pattern
        # The search-web said: https://careers.klm.com/[job-title]-[ID]
        # But looking at categories, they are https://careers.klm.com/en/job-area/technology/
        
        links = re.findall(r'https?://careers\.klm\.com/[^"\'>\s]+-\d{4,6}/?', res.text)
        if links:
            print(f"Found {len(set(links))} unique job-like links in source code.")
            for l in sorted(list(set(links)))[:20]:
                print(f"Link: {l}")
        else:
            # Maybe they are relative links
            rel_links = re.findall(r'/[^"\'>\s]+-\d{4,6}/?', res.text)
            if rel_links:
                 print(f"Found {len(set(rel_links))} unique relative job-like links.")
                 for l in sorted(list(set(rel_links)))[:20]:
                    print(f"Rel Link: {l}")

asyncio.run(main())
