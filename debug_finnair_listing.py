import asyncio
import json
import curl_cffi.requests as curl_requests

async def debug():
    url = "https://finnair.wd103.myworkdayjobs.com/wday/cxs/finnair/finnair/jobs"
    payload = {"appliedFacets": {}, "limit": 5, "offset": 0, "searchText": ""}
    
    response = curl_requests.post(
        url=url,
        json=payload,
        headers={"Accept": "application/json"},
        impersonate="chrome110"
    )
    
    if response.status_code == 200:
        data = response.json()
        for item in data.get('jobPostings', []):
            print(f"Title: {item.get('title')}")
            print(f"ExternalPath: {item.get('externalPath')}")
            print("-" * 20)
    else:
        print(f"Failed to fetch listing: {response.status_code}")

if __name__ == "__main__":
    asyncio.run(debug())
