import requests
from bs4 import BeautifulSoup

def test_avincis():
    print("\n--- Testing Avincis ---")
    r = requests.get("https://www.avincis.com/jobs/italy/")
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # Try to find jobs
    job_cards = soup.find_all(['article', 'div'], class_=lambda c: c and ('job' in c.lower() or 'vacancy' in c.lower() or 'position' in c.lower()))
    print(f"Found {len(job_cards)} potential job containers by class")
    
    # Just list some links
    links = soup.find_all('a')
    job_links = []
    for a in links:
        href = a.get('href', '')
        if 'job' in href.lower() or 'vacancy' in href.lower() or 'career' in href.lower():
            job_links.append((a.text.strip(), href))
            
    print(f"Found {len(job_links)} potential job links")
    for title, href in job_links[:10]:
        print(f"Title: {title}, Href: {href}")

test_avincis()
