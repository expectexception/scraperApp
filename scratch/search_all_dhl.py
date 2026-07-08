import requests

def search_all_dhl():
    print("Searching all DHL jobs...")
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    total_found = 0
    for i in range(0, 10000, 1000):
        payload = {
            "sortBy": "",
            "subsearch": "",
            "from": i,
            "jobs": True,
            "counts": True,
            "pageName": "search-results",
            "size": 1000,
            "clearAll": False,
            "jdsource": "facets",
            "isSliderEnable": True,
            "pageId": "page3",
            "siteType": "external",
            "ddoKey": "refineSearch",
            "refNum": "DHL"
        }
        
        try:
            resp = requests.post(
                "https://careers.dhl.com/widgets",
                headers=headers,
                json=payload,
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            raw_jobs = data.get("refineSearch", {}).get("data", {}).get("jobs", [])
            
            if not raw_jobs:
                break
                
            for j in raw_jobs:
                title = j.get("title", "").lower()
                if "network control" in title or "trip planner" in title:
                    print(f"FOUND: {j.get('title')} | Category: {j.get('category')} | Country: {j.get('country')}")
                    total_found += 1
        except Exception as e:
            print(f"Error at {i}: {e}")
            break
            
    print(f"Done. Found {total_found} jobs.")

search_all_dhl()
