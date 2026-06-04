import requests
from bs4 import BeautifulSoup

url = "https://careers-psaairlines.icims.com/jobs/search?in_iframe=1"
headers = {"User-Agent": "Mozilla/5.0"}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, 'html.parser')
rows = soup.find_all('div', class_='row')
for row in rows:
    a = row.find('a')
    if a and 'job' in a.get('href', ''):
        print(row.prettify())
        break
