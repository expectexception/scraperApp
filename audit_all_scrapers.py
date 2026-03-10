import os
import django
import sys
import subprocess
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_service.settings')
django.setup()

from scraper_manager.config import CONFIG
from jobs.models import Job
from scraper_manager.models import ScrapedURL

OUTPUT_FILE = '/home/null/.gemini/antigravity/brain/1fd18f91-4fe5-4209-a20c-05b9394d4cfc/scraper_audit_report.md'

def audit_scrapers():
    enabled_sites = [k for k, v in CONFIG['sites'].items() if v.get('enabled', False)]
    # Exclude already verified
    exclude = ['absjets', 'aegean', 'aena']
    sites_to_test = [s for s in enabled_sites if s not in exclude]

    print(f"Starting audit for {len(sites_to_test)} scrapers...")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("# Scraper Audit Report\n\n")
        f.write("This report details data extraction issues for each scraper (excluding already verified ones).\n\n")

    results = []

    for idx, site in enumerate(sites_to_test):
        print(f"[{idx+1}/{len(sites_to_test)}] Auditing {site}...")
        
        # Clean previous jobs
        Job.objects.filter(source=site).delete()
        ScrapedURL.objects.filter(source=site).delete()
        
        # Run scraper
        try:
            subprocess.run(
                ["python3", "manage.py", "run_scraper", site, "--max-jobs", "1"],
                cwd="/home/null/ifoaSpace/scraperApp",
                timeout=45,
                capture_output=True,
                text=True
            )
        except subprocess.TimeoutExpired:
            print(f"  -> Timeout")
            _write_report(site, ["Timed out after 45s"])
            continue
        except Exception as e:
            print(f"  -> Error: {e}")
            _write_report(site, [f"Scraper execution error: {e}"])
            continue

        # Check DB
        jobs = Job.objects.filter(source=site)
        if jobs.count() == 0:
            print(f"  -> No jobs found")
            _write_report(site, ["Failed to extract any jobs (0 found)."])
            continue
            
        job = jobs.first()
        issues = []
        
        title = job.title or ""
        location = job.location or ""
        desc = job.description or ""
        
        if not title or title.strip() == "" or title.lower() == "unknown title":
            issues.append("Missing or invalid Job Title")
        if not location or location.strip() == "" or location.lower() in ["unknown", "unknown location"]:
            issues.append("Missing or unknown Job Location")
        if not desc or len(desc.strip()) < 50:
            issues.append(f"Description is missing or too short (length: {len(desc)})")
        
        if not issues:
            print(f"  -> OK")
            issues.append("✅ Data extracted perfectly.")
        else:
            print(f"  -> Issues: {', '.join(issues)}")
            
        _write_report(site, issues, job)

def _write_report(site, issues, job=None):
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        f.write(f"## {site}\n")
        for i in issues:
            f.write(f"- {i}\n")
        
        if job and "✅" not in issues[0]:
            f.write(f"\n**Extracted Data Snapshot:**\n")
            f.write(f"- **Title:** {job.title}\n")
            f.write(f"- **Location:** {job.location}\n")
            f.write(f"- **Sample Desc:** {job.description[:150] if job.description else ''}...\n")
        f.write("\n---\n\n")

if __name__ == '__main__':
    audit_scrapers()
