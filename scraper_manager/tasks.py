"""
Celery Tasks for Scraper Manager
Allows scheduled scraping via Celery Beat
"""
from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task(name='scraper_manager.run_single_scraper', bind=True)
def run_single_scraper_task(self, scraper_name, max_jobs=None, max_pages=None, job_id=None):
    """
    Run a single scraper as a Celery task
    
    Args:
        scraper_name: Name of scraper to run
        max_jobs: Maximum number of jobs to scrape
        max_pages: Maximum number of pages to scrape
    
    Returns:
        dict: Results of scraper run
    """
    from .models import ScraperJob
    
    logger.info(f"🚀 Starting Celery task for scraper: {scraper_name}")
    
    # Use existing job or create a new one
    if job_id:
        try:
            job = ScraperJob.objects.get(id=job_id)
            job.status = 'running'
            job.started_at = timezone.now()
            # Merge parameters
            params = job.parameters or {}
            params['task_id'] = self.request.id
            job.parameters = params
            job.save()
        except ScraperJob.DoesNotExist:
            job = ScraperJob.objects.create(
                scraper_name=scraper_name,
                status='running',
                started_at=timezone.now(),
                triggered_by=f'celery_task_{self.request.id}',
                parameters={'max_jobs': max_jobs, 'max_pages': max_pages, 'task_id': self.request.id}
            )
    else:
        job = ScraperJob.objects.create(
            scraper_name=scraper_name,
            status='running',
            started_at=timezone.now(),
            triggered_by=f'celery_task_{self.request.id}',
            parameters={'max_jobs': max_jobs, 'max_pages': max_pages, 'task_id': self.request.id}
        )
    
    try:
        # Build command arguments
        args = [scraper_name]
        kwargs = {}
        if max_jobs:
            kwargs['max_jobs'] = max_jobs
        if max_pages:
            kwargs['max_pages'] = max_pages
        
        # Run scraper via management command
        call_command('run_scraper', *args, **kwargs)
        
        # Refresh job to get updated stats
        job.refresh_from_db()
        
        logger.info(f"✅ Scraper {scraper_name} completed: {job.jobs_found} jobs found")
        
        return {
            'status': 'success',
            'scraper_name': scraper_name,
            'job_id': job.id,
            'jobs_found': job.jobs_found,
            'jobs_new': job.jobs_new,
            'jobs_updated': job.jobs_updated,
            'execution_time': job.execution_time
        }
        
    except Exception as e:
        logger.error(f"❌ Scraper {scraper_name} failed: {e}", exc_info=True)
        
        job.status = 'failed'
        job.completed_at = timezone.now()
        job.error_message = str(e)
        job.save()
        
        return {
            'status': 'failed',
            'scraper_name': scraper_name,
            'job_id': job.id,
            'error': str(e)
        }


@shared_task(name='scraper_manager.run_all_scrapers', bind=True)
def run_all_scrapers_task(self, max_jobs=None, max_pages=None):
    """
    Run all enabled scrapers as a Celery task
    
    Args:
        max_jobs: Maximum number of jobs per scraper
        max_pages: Maximum number of pages per scraper
    
    Returns:
        dict: Aggregated results
    """
    from .models import ScraperConfig, ScraperJob
    from .config import CONFIG
    
    logger.info("🚀 Starting Celery task: Run all scrapers")
    
    # Get enabled scrapers
    enabled_scrapers = [
        name for name, site in CONFIG['sites'].items()
        if site.get('enabled', False)
    ]
    
    if not enabled_scrapers:
        logger.warning("No enabled scrapers found")
        return {
            'status': 'warning',
            'message': 'No enabled scrapers',
            'results': []
        }
    
    logger.info(f"Running {len(enabled_scrapers)} scrapers: {', '.join(enabled_scrapers)}")
    
    results = []
    for scraper_name in enabled_scrapers:
        try:
            result = run_single_scraper_task(scraper_name, max_jobs, max_pages)
            results.append(result)
        except Exception as e:
            logger.error(f"Error running {scraper_name}: {e}")
            results.append({
                'status': 'failed',
                'scraper_name': scraper_name,
                'error': str(e)
            })
    
    # Aggregate statistics
    total_jobs = sum(r.get('jobs_found', 0) for r in results)
    total_new = sum(r.get('jobs_new', 0) for r in results)
    successful = sum(1 for r in results if r.get('status') == 'success')
    
    logger.info(f"✅ All scrapers completed: {total_jobs} jobs found ({total_new} new)")
    
    return {
        'status': 'completed',
        'scrapers_run': len(enabled_scrapers),
        'successful': successful,
        'failed': len(enabled_scrapers) - successful,
        'total_jobs_found': total_jobs,
        'total_new_jobs': total_new,
        'results': results
    }


@shared_task(name='scraper_manager.cleanup_old_jobs')
def cleanup_old_scraper_jobs(days=30):
    """
    Clean up old scraper job records
    
    Args:
        days: Delete records older than this many days
    """
    from .models import ScraperJob
    from datetime import timedelta
    
    cutoff = timezone.now() - timedelta(days=days)
    
    old_jobs = ScraperJob.objects.filter(created_at__lt=cutoff)
    count = old_jobs.count()
    
    if count > 0:
        old_jobs.delete()
        logger.info(f"🗑️ Cleaned up {count} old scraper job records (older than {days} days)")
    
    return {
        'status': 'success',
        'deleted_count': count,
        'cutoff_date': cutoff.isoformat()
    }


@shared_task(name='scraper_manager.cleanup_inactive_urls')
def cleanup_inactive_urls(days=60):
    """
    Clean up old inactive scraped URLs
    
    Args:
        days: Delete inactive URLs older than this many days
    """
    from .models import ScrapedURL
    from datetime import timedelta
    
    cutoff = timezone.now() - timedelta(days=days)
    
    old_urls = ScrapedURL.objects.filter(
        is_active=False,
        last_scraped__lt=cutoff
    )
    count = old_urls.count()
    
    
    if count > 0:
        old_urls.delete()
        logger.info(f"🗑️ Cleaned up {count} inactive scraped URLs (older than {days} days)")
    
    return {
        'status': 'success',
        'deleted_count': count,
        'cutoff_date': cutoff.isoformat()
    }

# ============================================================================
# AUTO-SCHEDULE TASKS (called by Celery Beat based on AUTO_SCHEDULE config)
# ============================================================================

@shared_task(bind=True, name='scraper_manager.run_all_scrapers_task')
def run_all_scrapers_task(self, max_jobs=None, max_pages=None):
    """
    Run all enabled scrapers (called from AUTO_SCHEDULE)
    """
    logger.info(f"[AUTO-SCHEDULE] Starting run_all_scrapers_task")
    
    try:
        args = ['all']
        if max_jobs:
            args.extend(['--max-jobs', str(max_jobs)])
        if max_pages:
            args.extend(['--max-pages', str(max_pages)])
        
        call_command('run_scraper', *args, verbosity=2)
        
        from .models import ScraperJob
        latest_job = ScraperJob.objects.latest('created_at')
        logger.info(f"[AUTO-SCHEDULE] All scrapers completed: {latest_job.jobs_found} jobs found")
        
        return {
            'status': 'success',
            'jobs_found': latest_job.jobs_found,
            'jobs_new': latest_job.jobs_new,
        }
    except Exception as e:
        logger.error(f"[AUTO-SCHEDULE] Error running all scrapers: {e}")
        return {'status': 'error', 'error': str(e)}

@shared_task(bind=True, name='scraper_manager.run_specific_scrapers_task')
def run_specific_scrapers_task(self, scrapers=None, max_jobs=None, max_pages=None):
    """
    Run specific scrapers (called from AUTO_SCHEDULE for priority/specialty groups)
    """
    if not scrapers:
        scrapers = []
    
    logger.info(f"[AUTO-SCHEDULE] Starting run_specific_scrapers_task for: {scrapers}")
    
    try:
        for scraper_name in scrapers:
            args = [scraper_name]
            if max_jobs:
                args.extend(['--max-jobs', str(max_jobs)])
            if max_pages:
                args.extend(['--max-pages', str(max_pages)])
            
            call_command('run_scraper', *args, verbosity=1)
        
        logger.info(f"[AUTO-SCHEDULE] Completed scraping: {', '.join(scrapers)}")
        return {'status': 'success', 'scrapers': scrapers}
    except Exception as e:
        logger.error(f"[AUTO-SCHEDULE] Error running specific scrapers: {e}")
        return {'status': 'error', 'error': str(e)}

@shared_task(bind=True, name='scraper_manager.cleanup_old_jobs_task')
def cleanup_old_jobs_task(self, days=90):
    """
    Archive/cleanup jobs older than specified days
    """
    logger.info(f"[AUTO-SCHEDULE] Starting cleanup of jobs older than {days} days")
    
    try:
        from datetime import timedelta
        from jobs.models import Job
        
        cutoff_date = timezone.now() - timedelta(days=days)
        old_jobs = Job.objects.filter(created_at__lt=cutoff_date)
        count = old_jobs.count()
        
        logger.info(f"[AUTO-SCHEDULE] Found {count} jobs to archive")
        old_jobs.update(status='archived')
        
        logger.info(f"[AUTO-SCHEDULE] Archived {count} old jobs")
        return {'status': 'success', 'archived_count': count}
    except Exception as e:
        logger.error(f"[AUTO-SCHEDULE] Error during cleanup: {e}")
        return {'status': 'error', 'error': str(e)}

@shared_task(bind=True, name='scraper_manager.generate_scraper_report_task')
def generate_scraper_report_task(self):
    """
    Generate daily scraper report
    """
    logger.info(f"[AUTO-SCHEDULE] Generating daily scraper report")
    
    try:
        from django.db.models import Count, Sum, Avg
        from .models import ScraperJob
        
        today = timezone.now().date()
        today_jobs = ScraperJob.objects.filter(created_at__date=today)
        
        report = {
            'date': today.isoformat(),
            'total_runs': today_jobs.count(),
            'successful_runs': today_jobs.filter(status='completed').count(),
            'failed_runs': today_jobs.filter(status='failed').count(),
            'total_jobs_found': today_jobs.aggregate(Sum('jobs_found'))['jobs_found__sum'] or 0,
            'total_new_jobs': today_jobs.aggregate(Sum('jobs_new'))['jobs_new__sum'] or 0,
            'avg_execution_time': today_jobs.aggregate(Avg('execution_time'))['execution_time__avg'] or 0,
        }
        
        logger.info(f"[AUTO-SCHEDULE] Report generated: {report}")
        return report
    except Exception as e:
        logger.error(f"[AUTO-SCHEDULE] Error generating report: {e}")
        return {'status': 'error', 'error': str(e)}

@shared_task(name='scraper_manager.verify_active_jobs_task')
def verify_active_jobs_task(limit=200):
    """
    Verify status of currently active jobs in the background.
    """
    from .db_manager import DjangoDBManager
    import asyncio
    
    logger.info(f"🔍 Starting background job verification (limit={limit})")
    
    db = DjangoDBManager()
    
    # Run the async verification in the current event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    stats = loop.run_until_complete(db.verify_active_jobs(limit=limit))
    
    logger.info(f"✅ Job verification complete: {stats}")
    return stats

@shared_task(name='scraper_manager.full_maintenance_task')
def full_maintenance_task():
    """
    Run all maintenance tasks: cleanup, verification, reports.
    """
    logger.info("🛠️ Starting full system maintenance")
    
    # 1. Cleanup old scraper logs
    cleanup_old_scraper_jobs(days=30)
    
    # 2. Cleanup old inactive URLs
    cleanup_inactive_urls(days=60)
    
    # 3. Archive very old jobs
    cleanup_old_jobs_task(days=90)
    
    # 4. Verify active jobs (batch of 500)
    verify_active_jobs_task(limit=500)
    
    # 5. Generate report
    generate_scraper_report_task()
    
    logger.info("✅ Full system maintenance complete")
    return "Maintenance Complete"
