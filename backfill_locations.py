import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scraper_service.settings")
django.setup()

from jobs.models import Job
from scraper_manager.location_manager import LocationManager
from scraper_manager.db_manager import DjangoDBManager

db_mgr = DjangoDBManager()
jobs = Job.objects.all()
print(f"Total jobs to check: {jobs.count()}")

updated_count = 0
for job in jobs:
    raw_loc = job.raw_json.get("location", "") if job.raw_json else job.location
    if not raw_loc:
        raw_loc = job.location
    
    company = job.company or "Unknown"
    normalized_loc = LocationManager.normalize_location(raw_loc, company=company)
    
    # Extract country code
    country_code = db_mgr._extract_country_code(normalized_loc, company)
    
    if job.location != normalized_loc or job.country_code != country_code:
        print(f"Updating job {job.id}:")
        print(f"  Old Loc: {repr(job.location)} -> New Loc: {repr(normalized_loc)}")
        print(f"  Old CC: {repr(job.country_code)} -> New CC: {repr(country_code)}")
        job.location = normalized_loc
        job.country_code = country_code
        job.save()
        updated_count += 1

print(f"Backfill finished. Updated {updated_count} jobs.")
