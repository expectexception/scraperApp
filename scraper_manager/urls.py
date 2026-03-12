"""
URL configuration for scraper_manager app
"""

from django.urls import path
from . import api

app_name = 'scraper_manager'

urlpatterns = [
    # Health check (no auth required)
    path('health/', api.health_check, name='health'),

    # Dashboard auth
    path('auth/login/', api.dashboard_login, name='dashboard_login'),
    
    # List available scrapers (no auth required)
    path('list/', api.list_available_scrapers, name='list'),

    # List all scraper configs
    path('configs/', api.scraper_configs, name='configs'),
    
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

    # Get managed jobs from main jobs table
    path('jobs/', api.managed_jobs, name='managed_jobs'),

    # Update a stored job record
    path('jobs/<int:job_id>/', api.update_managed_job, name='update_managed_job'),
    
    # Get recent scraped jobs
    path('recent-jobs/', api.recent_jobs, name='recent_jobs'),

    # Get paginated scraped records
    path('scraped-records/', api.scraped_records, name='scraped_records'),
    
    # Get scraper configuration
    path('config/<str:scraper_name>/', api.scraper_config, name='config'),
    
    # Update scraper configuration
    path('config/<str:scraper_name>/update/', api.update_scraper_config, name='update_config'),

    # System metrics
    path('metrics/', api.system_metrics, name='system_metrics'),

    # Scheduling overview
    path('scheduler/overview/', api.scheduler_overview, name='scheduler_overview'),
]
