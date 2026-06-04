import requests
from bs4 import BeautifulSoup

url = "https://careers-psaairlines.icims.com/jobs/search?in_iframe=1"
headers = {"User-Agent": "Mozilla/5.0"}
resp = requests.get(url, headers=headers)
print("Status:", resp.status_code)
soup = BeautifulSoup(resp.text, 'html.parser')

job_links = soup.find_all('a', class_='iCIMS_Anchor')
print("Found iCIMS_Anchor links:", len(job_links))
for a in job_links[:5]:
    print(a.text.strip(), "->", a.get('href'))

# Also print out titles found in typical iCIMS lists
titles = soup.find_all('div', class_='title')
if titles:
    print("Found titles:", len(titles))
    for t in titles[:5]:
        print(t.text.strip())
        
# Try to find elements by other common iCIMS classes
rows = soup.find_all('div', class_='row')
print("Found rows:", len(rows))
for row in rows:
    a = row.find('a')
    if a and 'job' in a.get('href', ''):
        print(a.text.strip(), "->", a.get('href'))
        
