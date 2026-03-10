import asyncio
from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup
import json

async def klm():
    async with AsyncSession(impersonate="chrome110") as s:
        print("--- KLM ---")
        res = await s.get("https://careers.klm.com/en/jobs/")
        soup = BeautifulSoup(res.text, 'html.parser')
        # find job cards or job links
        links = soup.select('a[href*="/job/"]')
        for l in links[:5]:
            print(l.get_text(strip=True), l.get('href'))

async def ita():
    async with AsyncSession(impersonate="chrome110") as s:
        print("--- ITA ---")
        res = await s.get("https://career.ita-airways.com/search/")
        soup = BeautifulSoup(res.text, 'html.parser')
        links = soup.select('a.jobTitle-link, a[href*="/job/"]')
        if not links:
            # find any links that look like jobs
            for a in soup.find_all('a', href=True):
                h = a['href']
                if '/job/' in h or 'requisition' in h:
                    print(a.get_text(strip=True), h)
        else:
            for l in links[:5]:
                print(l.get_text(strip=True), l.get('href'))

async def main():
    await klm()
    await ita()

asyncio.run(main())
