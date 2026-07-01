import asyncio
from curl_cffi import requests

urls = {
    "quikjet": "https://quikjet.co.in/careers/",
    "indiaone": "https://www.indiaoneair.com/careers/",
    "qantas": "https://careers.qantas.com/jobs/jobs-in-operations-safety/?per_page=10",
    "chevron": "https://careers.chevron.com/category/aviation-jobs/35016/8307184/1",
    "transair": "https://transairhawaii.com/category/jobs/",
    "aaregional": "https://aaregional.wd503.myworkdayjobs.com/search",
    "magnifica": "https://magnificaair.com/careers/",
    "upmc": "https://careers.upmc.com/job-search-results/?category[]=Other",
    "gmr": "https://careers.gmr.net/gmr/jobs",
    "virgingalactic": "https://vgcareers.virgingalactic.com/global/en/search-results"
}

async def test_url(name, url):
    print(f"\n--- Testing {name} ---")
    try:
        # Use curl_cffi to bypass WAF
        r = requests.get(url, impersonate="chrome120", timeout=15)
        print(f"[{name}] Status: {r.status_code}")
        print(f"[{name}] Content length: {len(r.text)}")
        print(f"[{name}] Title: {r.text[:500].split('<title>')[-1].split('</title>')[0] if '<title>' in r.text else 'No Title'}")
        
        # Save first 500 chars of HTML
        print(f"[{name}] Snippet: {r.text[:300]}")
    except Exception as e:
        print(f"[{name}] Error: {e}")

async def main():
    for name, url in urls.items():
        await test_url(name, url)

if __name__ == "__main__":
    asyncio.run(main())
