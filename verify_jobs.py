import os
import django
import sys

# Ensure the project root is in the python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_service.settings')
django.setup()

from jobs.models import Job

jobs = Job.objects.all()
print(f"Total jobs: {jobs.count()}")
for job in jobs:
    print(f"[{job.company}] {job.title}")
    # print(f"URL: {job.url}")
    # print(f"Location: {job.location}")
    print("-" * 50)
