import os, sys, django, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_service.settings')
django.setup()
from scraper_manager.config import CONFIG

enabled_sites = sorted([k for k, v in CONFIG['sites'].items() if v.get('enabled', False)])
exclude = ['absjets', 'aegean', 'aena']
sites = [s for s in enabled_sites if s not in exclude]

start_idx = sites.index('falconaviation') + 1
print(f"Testing the next batch starting from {sites[start_idx]}")

for site in sites[start_idx:start_idx+10]:
    print(f"\n--- Testing {site} ---")
    try:
        subprocess.run(["python3", "manage.py", "run_scraper", site, "--max-jobs", "1"],
                       cwd="/home/rajat/Desktop/AeroOps Intel/scraper-standalone",
                       timeout=45)
    except subprocess.TimeoutExpired:
        print(f"!!! Timeout for {site} !!!")
