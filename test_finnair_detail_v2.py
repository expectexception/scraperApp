import asyncio
import json
import curl_cffi.requests as curl_requests

async def test():
    # Real path from Finnair listing
    external_path = "/job/Vantaa/Sourcing-Manager--Aircraft-Maintenance_R265750"
    api_url = f"https://finnair.wd103.myworkdayjobs.com/wday/cxs/finnair/finnair{external_path}"
    
    print(f"Fetching details from: {api_url}")
    response = curl_requests.get(
        url=api_url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
        },
        impersonate="chrome110"
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        job_description = data.get('jobPostingInfo', {}).get('jobDescription', '')
        print(f"Description length: {len(job_description)}")
        # print("\nDescription Snippet:")
        # print(job_description[:500])
    else:
        print(f"Body: {response.text[:200]}")

if __name__ == "__main__":
    asyncio.run(test())
