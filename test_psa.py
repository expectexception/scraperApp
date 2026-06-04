import requests
from bs4 import BeautifulSoup

url = "https://careers-psaairlines.icims.com/jobs/search?ss=1&hashed=-435589783"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
resp = requests.get(url, headers=headers)
print("Status:", resp.status_code)

soup = BeautifulSoup(resp.text, 'html.parser')
# iCIMS job lists are usually in a div with class iCIMS_JobsTable or similar, or .row / .col-xs-12
job_links = soup.find_all('a', class_='iCIMS_Anchor')
print("Found iCIMS_Anchor links:", len(job_links))
for a in job_links[:5]:
    print(a.text.strip(), "->", a.get('href'))
    
if not job_links:
    # See if it's an iframe wrapper
    iframe = soup.find('iframe')
    if iframe:
        print("Found iframe! src:", iframe.get('src'))
