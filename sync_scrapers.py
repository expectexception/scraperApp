import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_service.settings')
django.setup()
from scraper_manager.models import ScraperConfig
from scraper_manager.config import CONFIG

for site_key, site_val in CONFIG['sites'].items():
    if site_val.get('enabled', False):
        config, created = ScraperConfig.objects.get_or_create(scraper_name=site_key)
        if not config.is_enabled:
            config.is_enabled = True
            config.save()
            print(f"Enabled {site_key}")

print("Sync complete.")
