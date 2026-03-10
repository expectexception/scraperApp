import requests
import json
from bs4 import BeautifulSoup

urls = [
    "https://www.absjets.com/careers-109",
    "https://www.alsie.com/",
    "https://amapola.nu/",
    "https://cabotaviation.com/",
    "https://jdair.net",
    "https://hr.egyptair.com",
    "https://www.lot.com/uz/en/explore/about-lot/our-crew",
    "https://jobs.airarabiagroupcareers.com/search/",
    "https://ada.ae/general-application/",
    "https://falconaviation.ae/careers"
]

results = {}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

for url in urls:
    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text().lower()
        
        job_indicators = sum(1 for word in ['job', 'career', 'vacancy', 'apply', 'position'] if word in text)
        is_redirect = response.history != []
        final_url = response.url
        score = job_indicators
        
        # Check for specific link patterns
        links = soup.find_all('a', href=True)
        job_links = [l['href'] for l in links if any(w in l['href'].lower() for w in ['job', 'career', 'vacancy'])]
        
        results[url] = {
            'status_code': response.status_code,
            'final_url': final_url,
            'job_keyword_score': score,
            'job_links_found': len(job_links) > 0,
            'sample_job_links': list(set(job_links))[:3]
        }
    except Exception as e:
        results[url] = {'error': str(e)}

print(json.dumps(results, indent=2))
