import requests
from bs4 import BeautifulSoup

url = "https://careers-psaairlines.icims.com/jobs/search?in_iframe=1&pr=1"
headers = {"User-Agent": "Mozilla/5.0"}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, 'html.parser')
job_links = soup.find_all('a', class_='iCIMS_Anchor')
print(f"Page 1 found {len(job_links)} jobs")
for a in job_links[:2]:
    print(a.text.strip())
