import os
import django
import sys

print("Setting DJANGO_SETTINGS_MODULE...")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_service.settings')
print("Calling django.setup()...")
try:
    django.setup()
    print("Django setup successful!")
    from django.conf import settings
    print(f"DATABASES['default']: {settings.DATABASES['default']}")
except Exception as e:
    print(f"Django setup failed: {e}")

from scraper_manager.scrapers import list_scrapers
print(f"Available scrapers: {list_scrapers()}")
