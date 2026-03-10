import os, sys, django, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_service.settings')
django.setup()
from scraper_manager.config import CONFIG
from jobs.models import Job
from scraper_manager.models import ScrapedURL

OUTPUT_FILE = '/home/rajat/.gemini/antigravity/brain/a1d52894-5c28-497f-8a62-1eb517f7fada/scraper_audit_report.md'
enabled_sites = sorted([k for k, v in CONFIG['sites'].items() if v.get('enabled', False)])
exclude = ['absjets', 'aegean', 'aena']
sites = [s for s in enabled_sites if s not in exclude]

# Find index of eurowings
start_idx = sites.index('eurowings') + 1

print(f"Starting audit from index {start_idx} (total {len(sites)})...")
for idx, site in enumerate(sites[start_idx:], start=start_idx):
    print(f"[{idx+1}/{len(sites)}] Auditing {site}...")
    Job.objects.filter(source=site).delete()
    ScrapedURL.objects.filter(source=site).delete()
    
    try:
        subprocess.run(["python3", "manage.py", "run_scraper", site, "--max-jobs", "1"],
                       cwd="/home/rajat/Desktop/AeroOps Intel/scraper-standalone",
                       timeout=120, capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        print(f"  -> Timeout")
        with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
            f.write(f"## {site}\n- Timed out after 120s\n\n---\n\n")
        continue

    jobs = Job.objects.filter(source=site)
    if jobs.count() == 0:
        print(f"  -> 0 found")
        with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
            f.write(f"## {site}\n- Failed to extract any jobs (0 found).\n\n---\n\n")
        continue
    
    job = jobs.first()
    issues = []
    if not job.title or job.title.strip() == "": issues.append("Missing Title")
    if not job.location or job.location.strip() == "": issues.append("Missing Location")
    if not job.description or len(job.description.strip()) < 50: issues.append("Missing Description")
    
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        f.write(f"## {site}\n")
        if not issues:
            print("  -> OK")
            f.write("- ✅ Data extracted perfectly.\n\n---\n\n")
        else:
            print("  -> Issues:", ", ".join(issues))
            for i in issues: f.write(f"- {i}\n")
            f.write("\n---\n\n")

print("Done.")
