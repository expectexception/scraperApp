import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backendMain.settings')
django.setup()

from jobs.models import Job

sources = ['rtx', 'dhl', 'flexjet', 'ups', 'airarabia', 'jet2', 'amazon_air', 'transavia_fr']

for source in sources:
    print(f"=== {source} ===")
    jobs = Job.objects.filter(source=source)
    print(f"Total jobs: {jobs.count()}")
    
    apply_links = 0
    detail_links = 0
    other_links = 0
    
    for job in jobs[:10]:
        print(f"  - {job.title}: {job.url}")
        if 'apply' in job.url.lower():
            apply_links += 1
        else:
            detail_links += 1
            
    print(f"Summary: Apply-like links in top 10: {apply_links}, Detail-like links: {detail_links}")
    print()
