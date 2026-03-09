"""
URL configuration for scraper_manager app
"""

from django.urls import path
from . import api

app_name = 'scraper_manager'

urlpatterns = [
    # Health check (no auth required)
    path('health/', api.health_check, name='health'),
    
    # List available scrapers (no auth required)
    path('list/', api.list_available_scrapers, name='list'),
    
    # Start single scraper
    path('start/', api.start_scraper, name='start'),
    
    # Start all scrapers
    path('start-all/', api.run_all_scrapers, name='start_all'),
    
    # Check scraper status
    path('status/<int:job_id>/', api.scraper_status, name='status'),
    
    # Cancel scraper job
    path('cancel/<int:job_id>/', api.cancel_scraper_job, name='cancel'),
    
    # Get active jobs
    path('active/', api.active_jobs, name='active'),
    
    # Get statistics
    path('stats/', api.scraper_stats, name='stats'),
    
    # Get history
    path('history/', api.scraper_history, name='history'),
    
    # Get recent scraped jobs
    path('recent-jobs/', api.recent_jobs, name='recent_jobs'),
    
    # Get scraper configuration
    path('config/<str:scraper_name>/', api.scraper_config, name='config'),
    
    # Update scraper configuration
    path('config/<str:scraper_name>/update/', api.update_scraper_config, name='update_config'),
]
