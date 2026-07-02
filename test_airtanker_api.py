import urllib.request
import json

url = "https://airtanker.pinpointhq.com/postings.json"
req = urllib.request.Request(
    url, 
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'}
)
try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(f"Success! Found {len(data.get('data', []))} jobs.")
        if data.get('data'):
            sample = data['data'][0]
            print("Sample job keys:", sample.keys())
            print("Title:", sample.get('title'))
            print("URL:", sample.get('url'))
            print("Location:", sample.get('location'))
            print("Department:", sample.get('department'))
except Exception as e:
    print("Error:", e)
