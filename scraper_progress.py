import os
import django
import sys

# Ensure the project root is in the python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_service.settings')
django.setup()

from scraper_manager.models import ScraperJob
from scraper_manager.config import CONFIG
enabled_scrapers = [k for k, v in CONFIG['sites'].items() if v.get('enabled')]

total_scrapers = len(enabled_scrapers)
completed_jobs = ScraperJob.objects.all()

completed_count = completed_jobs.count()
success_objs = completed_jobs.filter(status='completed')
failed_objs = completed_jobs.filter(status='failed')

print(f"--- SCRAPER PROGRESS ---")
print(f"Total scrapers to run: {total_scrapers}")
print(f"Jobs completed/attempted: {completed_count}")
print(f"Successful: {success_objs.count()}")
print(f"Failed: {failed_objs.count()}")

if failed_objs.count() > 0:
    print("\nFailed Scrapers:")
    for f in failed_objs:
        print(f"  - {f.scraper_name}: {f.error_message}")

print(f"\nCompletion: {completed_count}/{total_scrapers} ({(completed_count/total_scrapers)*100:.1f}%)")
