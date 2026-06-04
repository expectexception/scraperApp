import requests
import json
import re

url = "https://careers-psaairlines.icims.com/jobs/search?ss=1&hashed=-435589783"
headers = {"User-Agent": "Mozilla/5.0"}
resp = requests.get(url, headers=headers)
html = resp.text

lines = html.split('\n')
for i, line in enumerate(lines):
    if 'Dispatch' in line or 'row' in line.lower() or 'job' in line.lower():
        if 'Aircraft Dispatch Coordinator' in line:
            print("Found job title in line:", i)
            print(line.strip()[:200])

    if 'href' in line and 'jobs' in line and '/job' in line:
        pass # we can look for job links
