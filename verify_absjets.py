import os
import django
import sys
import json

# Ensure the project root is in the python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_service.settings')
django.setup()

from jobs.models import Job

jobs = Job.objects.filter(source='absjets')
for job in jobs:
    print(f"[{job.company}] {job.title}")
    print(f"URL: {job.url}")
    print(f"Location: {job.location}")
    print(f"Posted: {job.posted_date}")
    print(f"Salary: {job.salary_min} - {job.salary_max} {job.salary_currency}")
    print(f"Description snippet: {job.description[:200]}")
    print("-" * 50)
