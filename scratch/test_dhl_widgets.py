import requests
import json

def fetch_dhl_jobs():
    print("Fetching DHL jobs...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "sortBy": "",
        "subsearch": "",
        "from": 0,
        "jobs": True,
        "counts": True,
        "all_fields": [
            "category", "country", "state", "city", "type", "employmentType", "jobLevel"
        ],
        "pageName": "search-results",
        "size": 1000,
        "clearAll": False,
        "jdsource": "facets",
        "isSliderEnable": True,
        "pageId": "page3",
        "siteType": "external",
        "ddoKey": "refineSearch",
        "refNum": "DHL",
        "keyword": "Network Control Group"
    }
    
    try:
        resp = requests.post(
            "https://careers.dhl.com/widgets",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        raw_jobs = data.get("refineSearch", {}).get("data", {}).get("jobs", [])
        
        print(f"Total jobs returned in 'Freight Transportations and Aviation': {len(raw_jobs)}")
        
        matches = []
        for j in raw_jobs:
            title = j.get("title", "").lower()
            if "network" in title or "control" in title or "trip" in title or "planner" in title:
                matches.append(j.get("title"))
                
        print(f"Found {len(matches)} interesting titles:")
        for m in set(matches):
            print(f"- {m}")
            
    except Exception as e:
        print(f"Error: {e}")

fetch_dhl_jobs()
