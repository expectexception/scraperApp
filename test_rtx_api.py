import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Try different payloads
payloads = [
    # 1. Original payload
    {
        "sortBy": "",
        "subsearch": "",
        "from": 0,
        "jobs": True,
        "counts": True,
        "all_fields": ["category", "country", "state", "city", "type", "employmentType", "jobLevel"],
        "pageName": "search-results",
        "size": 1000,
        "clearAll": False,
        "jdsource": "facets",
        "isSliderEnable": True,
        "pageId": "page3",
        "siteType": "external",
        "ddoKey": "refineSearch",
        "refNum": "RTX",
    },
    # 2. No refNum
    {
        "sortBy": "",
        "subsearch": "",
        "from": 0,
        "jobs": True,
        "counts": True,
        "all_fields": ["category", "country", "state", "city", "type", "employmentType", "jobLevel"],
        "pageName": "search-results",
        "size": 1000,
        "clearAll": False,
        "jdsource": "facets",
        "isSliderEnable": True,
        "pageId": "page3",
        "siteType": "external",
        "ddoKey": "refineSearch",
    },
    # 3. Keyword "operations"
    {
        "sortBy": "",
        "subsearch": "",
        "from": 0,
        "jobs": True,
        "counts": True,
        "all_fields": ["category", "country", "state", "city", "type", "employmentType", "jobLevel"],
        "pageName": "search-results",
        "size": 1000,
        "clearAll": False,
        "jdsource": "facets",
        "isSliderEnable": True,
        "pageId": "page3",
        "siteType": "external",
        "ddoKey": "refineSearch",
        "refNum": "RTX",
        "keyword": "operations"
    }
]

for idx, p in enumerate(payloads):
    try:
        resp = requests.post("https://careers.rtx.com/widgets", headers=headers, json=p, timeout=10)
        data = resp.json()
        jobs = data.get("refineSearch", {}).get("data", {}).get("jobs", [])
        total = data.get("refineSearch", {}).get("data", {}).get("totalHits", 0)
        print(f"Payload {idx+1}: jobs returned: {len(jobs)}, totalHits: {total}")
    except Exception as e:
        print(f"Payload {idx+1} failed: {e}")
