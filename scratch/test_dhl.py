import requests
import json

def fetch_dhl_jobs():
    print("Fetching DHL jobs...")
    url = "https://careers.dhl.com/api/jobs"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "from": 0,
        "size": 1000,
        "query": "",
        "sortBy": "postedDate",
        "descending": True
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        data = response.json()
        
        jobs = data.get("hits", [])
        print(f"Total jobs returned: {len(jobs)}")
        
        matches = []
        for job in jobs:
            title = job.get("title", "").lower()
            if "network" in title or "control" in title or "trip" in title or "planner" in title:
                matches.append(job.get("title"))
                
        print(f"Found {len(matches)} interesting titles:")
        for m in set(matches):
            print(f"- {m}")
            
    except Exception as e:
        print(f"Error: {e}")

fetch_dhl_jobs()
