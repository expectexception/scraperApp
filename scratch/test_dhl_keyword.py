import requests

def search_dhl_keyword(keyword):
    print(f"Searching for '{keyword}'...")
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "keyword": keyword,
        "from": 0,
        "size": 100,
        "siteType": "external",
        "ddoKey": "refineSearch",
        "refNum": "DHL"
    }
    
    try:
        resp = requests.post(
            "https://careers.dhl.com/widgets",
            headers=headers,
            json=payload,
            timeout=10,
        )
        data = resp.json()
        raw_jobs = data.get("refineSearch", {}).get("data", {}).get("jobs", [])
        
        print(f"Total jobs returned: {len(raw_jobs)}")
        
        for j in raw_jobs:
            title = j.get("title", "")
            if keyword.lower() in title.lower():
                print(f"- {title}")
                print(f"  Category: {j.get('category')}")
            
    except Exception as e:
        print(f"Error: {e}")

search_dhl_keyword("Network Control Group")
search_dhl_keyword("Trip Planner")
