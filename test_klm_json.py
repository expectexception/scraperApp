import asyncio
from curl_cffi.requests import AsyncSession
import re

async def main():
    url = "https://careers.klm.com/en/jobs/?page=1"
    async with AsyncSession(impersonate="chrome110") as s:
        print(f"Fetching {url}...")
        try:
            res = await s.get(url, timeout=30)
            print(f"Status: {res.status_code}")
            
            # Look for large JSON blocks in scripts
            # Pattern: <script ...>...{...}...</script>
            scripts = re.findall(r'<script.*?>([\s\S]*?)</script>', res.text)
            print(f"Found {len(scripts)} script tags.")
            
            for i, script in enumerate(scripts):
                if 'JSON.parse' in script or '{' in script:
                    # Look for job-like keywords
                    if 'job' in script.lower() or 'vacancy' in script.lower():
                        print(f"Script {i} contains job-related keywords. Length: {len(script)}")
                        # Print a snippet
                        print(script[:500] + "...")
                        
            # Just search for strings that look like IDs
            # Typical KLM ID might be 5 digits
            ids = re.findall(r'-\d{4,6}', res.text)
            if ids:
                print(f"Found potential IDs in text: {ids[:20]}")

        except Exception as e:
            print(f"Error: {e}")

asyncio.run(main())
