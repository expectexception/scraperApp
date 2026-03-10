import asyncio
from curl_cffi.requests import AsyncSession

async def main():
    async with AsyncSession(impersonate="chrome110") as s:
        res = await s.get("https://www.icelandair.com/about/job-vacancies/")
        print("Status", res.status_code)
        text = res.text
        print("Contains 'job':", "job" in text.lower())
        print("Contains 'careers':", "career" in text.lower())
        print("Contains 'vacancy':", "vacancy" in text.lower())
        # Print a few links
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(text, 'html.parser')
        links = soup.find_all('a')
        print(f"Total links: {len(links)}")
        for l in links[:20]:
            h = l.get('href', '')
            if 'job' in h.lower() or 'vacancy' in h.lower():
                print(f"Link: {h}")

asyncio.run(main())
