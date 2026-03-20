"""
REST API views for scraper management
"""

import logging
import os
import secrets
import subprocess
import sys
import json
import signal
import psutil
import requests
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.db.models import Count, Avg, Sum, Q
from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.core.paginator import Paginator

from .models import ScraperJob, ScraperConfig, ScrapedURL
from .config import CONFIG
from .scrapers import list_scrapers
from jobs.models import Job
from .category_taxonomy import normalize_job_categories

try:
    from django_celery_beat.models import PeriodicTask, CrontabSchedule
    CELERY_BEAT_AVAILABLE = True
except Exception:
    PeriodicTask = None
    CrontabSchedule = None
    CELERY_BEAT_AVAILABLE = False

# Setup logging
logger = logging.getLogger(__name__)
TOKEN_TTL_SECONDS = 60 * 60 * 12  # 12 hours
TOKEN_SALT = "scraper-dashboard-auth"


def _dashboard_credentials() -> tuple[str, str | None]:
    return (
        getattr(settings, "DASHBOARD_USERNAME", "admin"),
        getattr(settings, "DASHBOARD_PASSWORD", None),
    )


def _issue_dashboard_token(username: str) -> str:
    payload = {
        "username": username,
        "nonce": secrets.token_urlsafe(16),
    }
    return signing.dumps(payload, salt=TOKEN_SALT)


def _require_dashboard_auth(request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return Response({"error": "Authorization bearer token required"}, status=status.HTTP_401_UNAUTHORIZED)

    token = auth_header.split(" ", 1)[1].strip()
    try:
        token_data = signing.loads(token, salt=TOKEN_SALT, max_age=TOKEN_TTL_SECONDS)
    except signing.SignatureExpired:
        return Response({"error": "Token expired"}, status=status.HTTP_401_UNAUTHORIZED)
    except signing.BadSignature:
        return Response({"error": "Invalid or expired token"}, status=status.HTTP_401_UNAUTHORIZED)

    return token_data.get("username", "dashboard")


def _dispatch_scraper_job(scraper_name: str, job_id: str, max_jobs=None, max_pages=None, job_categories=None) -> int:
    """Dispatch scraper command in background without Celery dependency."""
    manage_py = os.path.join(settings.BASE_DIR, "manage.py")
    cmd = [sys.executable, manage_py, "run_scraper", scraper_name, "--job-id", str(job_id)]
    if max_jobs:
        cmd.extend(["--max-jobs", str(max_jobs)])
    if max_pages:
        cmd.extend(["--max-pages", str(max_pages)])
    normalized_categories = normalize_job_categories(job_categories)
    if normalized_categories:
        cmd.append("--job-categories")
        cmd.extend(normalized_categories)
    process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return process.pid


def _job_pk(job: ScraperJob) -> str:
    """Return a saved job primary key for compatibility with both SQL and MongoDB."""
    if job.pk is None:
        raise ValueError("ScraperJob must be saved before dispatch")
    return str(job.pk)


def _serialize_schedule_snapshot(config: ScraperConfig) -> dict:
    task_name = f"scraper_{config.scraper_name}_managed"
    periodic_task = None
    if CELERY_BEAT_AVAILABLE and PeriodicTask is not None:
        periodic_task = PeriodicTask.objects.filter(name=task_name).first()

    return {
        'scraper_name': config.scraper_name,
        'schedule_enabled': config.schedule_enabled,
        'schedule_cron': config.schedule_cron,
        'task_name': task_name,
        'celery_beat_available': CELERY_BEAT_AVAILABLE,
        'periodic_task_enabled': bool(periodic_task.enabled) if periodic_task else False,
        'periodic_task_exists': periodic_task is not None,
        'last_run': config.last_run,
    }


def _sync_scraper_schedule(config: ScraperConfig) -> dict:
    if not CELERY_BEAT_AVAILABLE:
        return {
            'celery_beat_available': False,
            'synced': False,
            'reason': 'django_celery_beat is not available',
        }
    assert PeriodicTask is not None
    assert CrontabSchedule is not None

    task_name = f"scraper_{config.scraper_name}_managed"
    if not config.schedule_enabled or not config.schedule_cron:
        PeriodicTask.objects.filter(name=task_name).update(enabled=False)
        return {
            'celery_beat_available': True,
            'synced': True,
            'task_name': task_name,
            'enabled': False,
        }

    cron_parts = config.schedule_cron.split()
    if len(cron_parts) != 5:
        raise ValueError('schedule_cron must have 5 parts: minute hour day month weekday')

    minute, hour, day_of_month, month_of_year, day_of_week = cron_parts
    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute=minute,
        hour=hour,
        day_of_month=day_of_month,
        month_of_year=month_of_year,
        day_of_week=day_of_week,
        timezone=getattr(settings, 'TIME_ZONE', 'UTC'),
    )
    enabled = bool(config.is_enabled and config.schedule_enabled)
    task, _ = PeriodicTask.objects.update_or_create(
        name=task_name,
        defaults={
            'task': 'scraper_manager.run_single_scraper',
            'crontab': schedule,
            'enabled': enabled,
            'kwargs': json.dumps({
                'scraper_name': config.scraper_name,
                'max_jobs': config.max_jobs,
                'max_pages': config.max_pages,
            }),
            'description': f'Managed schedule for {config.scraper_name}',
        }
    )

    return {
        'celery_beat_available': True,
        'synced': True,
        'task_name': task.name,
        'enabled': enabled,
    }


def _build_job_summary(queryset):
    return queryset.aggregate(
        total=Count('id'),
        new=Count('id', filter=Q(status='new')),
        active=Count('id', filter=Q(status='active')),
        closed=Count('id', filter=Q(status='closed')),
        verified=Count('id', filter=Q(is_verified=True)),
    )


def _is_truthy(value) -> bool:
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _check_job_url(job: Job) -> dict:
    """Check job URL and update job status/last_checked."""
    if not job.url:
        return {
            'result': 'skipped_no_url',
            'error': 'Job has no URL to check',
            'status_changed': False,
            'status': job.status,
        }

    previous_status = job.status
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(job.url, headers=headers, timeout=12, allow_redirects=True)
    except requests.RequestException as exc:
        return {
            'result': 'request_failed',
            'error': str(exc),
            'status_changed': False,
            'status': job.status,
        }

    result = 'active'
    should_mark_closed = False
    if response.status_code in [404, 410]:
        should_mark_closed = True
        result = 'closed_status_code'
    else:
        closed_keywords = [
            'position no longer available',
            'job is closed',
            'no longer accepting applications',
            'this job has expired',
            'position has been filled',
            'job not found',
            'page not found',
            'opportunity has passed',
            'no longer active'
        ]
        content_lower = response.text.lower()
        if any(keyword in content_lower for keyword in closed_keywords):
            should_mark_closed = True
            result = 'closed_keyword_match'
        else:
            result = 'active' if previous_status != 'closed' else 'was_closed_now_seems_active'

    if should_mark_closed:
        job.status = 'closed'

    job.last_checked = timezone.now()
    update_fields = ['last_checked']
    if job.status != previous_status:
        update_fields.append('status')
    job.save(update_fields=update_fields)

    return {
        'result': result,
        'error': None,
        'status_changed': job.status != previous_status,
        'status': job.status,
        'last_checked': job.last_checked,
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def dashboard_login(request):
    """Authenticate dashboard user and return short-lived bearer token."""
    expected_user, expected_password = _dashboard_credentials()
    username = request.data.get('username')
    password = request.data.get('password')
    
    expected_user, expected_password = _dashboard_credentials()
    username = request.data.get('username')
    password = request.data.get('password')

    if not expected_password:
        return Response({'error': 'Dashboard password is not configured'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    if username != expected_user or password != expected_password:
        return Response({'error': 'Invalid username or password'}, status=status.HTTP_401_UNAUTHORIZED)

    token = _issue_dashboard_token(username)
    return Response({
        'token': token,
        'expires_in': TOKEN_TTL_SECONDS,
        'username': username,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def list_available_scrapers(request):
    """List all available scrapers"""
    config_map = {cfg.scraper_name: cfg for cfg in ScraperConfig.objects.all()}
    active_map = dict(
        ScraperJob.objects.filter(status__in=['pending', 'running'])
        .values_list('scraper_name')
        .annotate(count=Count('id'))
    )
    scrapers = []
    
    for scraper_name in list_scrapers():
        site_config = CONFIG['sites'].get(scraper_name, {})
        scraper_config = CONFIG['scrapers'].get(scraper_name, {})
        db_config = config_map.get(scraper_name)
        schedule_snapshot = _serialize_schedule_snapshot(db_config) if db_config else {
            'schedule_enabled': False,
            'schedule_cron': '',
            'periodic_task_enabled': False,
            'periodic_task_exists': False,
            'celery_beat_available': CELERY_BEAT_AVAILABLE,
        }
        
        scrapers.append({
            'name': scraper_name,
            'display_name': site_config.get('name', scraper_name),
            'description': site_config.get('description', ''),
            'enabled': db_config.is_enabled if db_config else site_config.get('enabled', False),
            'base_url': site_config.get('base_url', ''),
            'max_jobs': db_config.max_jobs if db_config else scraper_config.get('max_jobs'),
            'max_pages': db_config.max_pages if db_config else scraper_config.get('max_pages'),
            'timeout': db_config.timeout if db_config else 300,
            'retry_count': db_config.retry_count if db_config else 3,
            'active_jobs': active_map.get(scraper_name, 0),
            'schedule': schedule_snapshot,
        })
    
    return Response({'scrapers': scrapers})


@api_view(['GET'])
@permission_classes([AllowAny])
def scraper_configs(request):
    """Return all scraper configs for dashboard editing."""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user

    existing_configs = {cfg.scraper_name: cfg for cfg in ScraperConfig.objects.all()}
    configs = {}
    for scraper_name in list_scrapers():
        cfg = existing_configs.get(scraper_name)
        site_config = CONFIG['sites'].get(scraper_name, {})
        scraper_config = CONFIG['scrapers'].get(scraper_name, {})
        configs[scraper_name] = {
            'scraper_name': scraper_name,
            'is_enabled': cfg.is_enabled if cfg else site_config.get('enabled', False),
            'max_jobs': cfg.max_jobs if cfg else scraper_config.get('max_jobs'),
            'max_pages': cfg.max_pages if cfg else scraper_config.get('max_pages'),
            'timeout': cfg.timeout if cfg else 300,
            'retry_count': cfg.retry_count if cfg else 3,
            'schedule_enabled': cfg.schedule_enabled if cfg else False,
            'schedule_cron': cfg.schedule_cron if cfg else '',
            'description': cfg.description if cfg else site_config.get('description', ''),
            'last_run': cfg.last_run if cfg else None,
        }
    return Response({'configs': configs})


@api_view(['POST'])
@permission_classes([AllowAny])
def start_scraper(request):
    """Start a scraper job"""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user

    scraper_name = request.data.get('scraper_name')
    max_jobs = request.data.get('max_jobs')
    max_pages = request.data.get('max_pages')
    job_categories = normalize_job_categories(request.data.get('job_categories'))
    
    logger.info(f"API request to start scraper: {scraper_name} by {auth_user}")
    
    if not scraper_name:
        logger.warning("Scraper start request missing scraper_name")
        return Response(
            {'error': 'scraper_name is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if scraper_name not in list_scrapers() and scraper_name != 'all':
        logger.warning(f"Unknown scraper requested: {scraper_name}")
        return Response(
            {'error': f'Unknown scraper: {scraper_name}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if scraper_name != 'all':
        scraper_config = ScraperConfig.objects.filter(scraper_name=scraper_name).first()
        is_enabled = scraper_config.is_enabled if scraper_config else CONFIG['sites'].get(scraper_name, {}).get('enabled', False)
        if not is_enabled:
            return Response(
                {'error': f'Scraper {scraper_name} is disabled in configuration'},
                status=status.HTTP_409_CONFLICT,
            )
    
    # Check if scraper is already running
    active_jobs = ScraperJob.objects.filter(
        scraper_name=scraper_name,
        status__in=['pending', 'running']
    ).count()
    
    if active_jobs > 0:
        logger.warning(f"Scraper {scraper_name} already has {active_jobs} active job(s)")
        return Response(
            {'error': f'Scraper {scraper_name} is already running ({active_jobs} active job(s))', 
             'active_jobs': active_jobs},
            status=status.HTTP_409_CONFLICT
        )
    
    # Create job
    scraper_job = ScraperJob.objects.create(
        scraper_name=scraper_name,
        status='pending',
        triggered_by=auth_user,
        parameters={
            'max_jobs': max_jobs,
            'max_pages': max_pages,
            'job_categories': job_categories,
        }
    )
    scraper_job_id = _job_pk(scraper_job)
    
    logger.info(f"Created ScraperJob {scraper_job_id} for {scraper_name}")
    
    try:
        process_pid = _dispatch_scraper_job(
            scraper_name,
            scraper_job_id,
            max_jobs=max_jobs,
            max_pages=max_pages,
            job_categories=job_categories,
        )
        scraper_job.pid = process_pid
        scraper_job.save(update_fields=['pid'])
        logger.info(f"Dispatched ScraperJob {scraper_job_id} for background execution")
        
        return Response({
            'job_id': scraper_job_id,
            'scraper_name': scraper_name,
            'status': 'pending',
            'pid': process_pid,
            'message': 'Scraper job queued'
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Failed to dispatch scraper {scraper_name}: {e}", exc_info=True)
        scraper_job.status = 'failed'
        scraper_job.error_message = f"Dispatch failed: {str(e)}"
        scraper_job.save()
        
        return Response(
            {'error': f"Failed to queue job: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def scraper_status(request, job_id):
    """Get status of a scraper job"""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user

    try:
        job = ScraperJob.objects.get(pk=job_id)
        response_job_id = _job_pk(job)
        
        return Response({
            'job_id': response_job_id,
            'scraper_name': job.scraper_name,
            'status': job.status,
            'pid': job.pid,
            'progress': job.progress,
            'started_at': job.started_at,
            'completed_at': job.completed_at,
            'execution_time': job.execution_time,
            'jobs_found': job.jobs_found,
            'jobs_new': job.jobs_new,
            'jobs_updated': job.jobs_updated,
            'jobs_duplicate': job.jobs_duplicate,
            'error_message': job.error_message,
            'output_file': job.output_file,
            'parameters': job.parameters,
            'triggered_by': job.triggered_by,
        })
        
    except ScraperJob.DoesNotExist:
        return Response(
            {'error': 'Job not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def scraper_stats(request):
    """Get overall scraper statistics with optimized queries"""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user
    
    # Try to get stats from cache (5 min TTL)
    cache_key = 'scraper_stats_summary'
    cached_stats = cache.get(cache_key)
    if cached_stats and not request.query_params.get('fresh'):
        logger.debug("Returning cached scraper stats")
        return Response(cached_stats)
    
    # Aggregate all stats in single query
    job_stats = ScraperJob.objects.aggregate(
        total_runs=Count('id'),
        completed_runs=Count('id', filter=Q(status='completed')),
        failed_runs=Count('id', filter=Q(status='failed')),
        avg_time=Avg('execution_time', filter=Q(status='completed', execution_time__isnull=False)),
        total_new=Sum('jobs_new'),
        total_found=Sum('jobs_found')
    )
    
    # Get source distribution
    jobs_by_source = dict(
        ScrapedURL.objects.values('source')
        .annotate(count=Count('id'))
        .values_list('source', 'count')
    )
    
    # Get recent jobs efficiently
    recent_jobs = list(
        ScraperJob.objects
        .only('id', 'scraper_name', 'status', 'started_at', 'jobs_found')
        .order_by('-created_at')[:10]
        .values('id', 'scraper_name', 'status', 'started_at', 'jobs_found')
    )
    
    # Convert ObjectIds to strings for JSON serialization
    for rj in recent_jobs:
        if 'id' in rj:
            rj['id'] = str(rj['id'])
    
    stats_response = {
        'total_runs': job_stats['total_runs'] or 0,
        'completed_runs': job_stats['completed_runs'] or 0,
        'failed_runs': job_stats['failed_runs'] or 0,
        'success_rate': (job_stats['completed_runs'] / job_stats['total_runs'] * 100) if job_stats['total_runs'] > 0 else 0,
        'total_jobs_scraped': job_stats['total_found'] or 0,
        'total_new_jobs': job_stats['total_new'] or 0,
        'jobs_by_source': jobs_by_source,
        'avg_execution_time': round(job_stats['avg_time'] or 0, 2),
        'recent_jobs': recent_jobs,
        'job_status_summary': _build_job_summary(Job.objects.all()),
    }
    
    # Cache for 5 minutes
    cache.set(cache_key, stats_response, 300)
    return Response(stats_response)


@api_view(['GET'])
@permission_classes([AllowAny])
def scraper_history(request):
    """Get scraper execution history with pagination and filtering"""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user
    
    scraper_name = request.query_params.get('scraper')
    search = (request.query_params.get('q') or '').strip()
    page = max(int(request.query_params.get('page', 1)), 1)
    limit = min(max(int(request.query_params.get('limit', 20)), 1), 100)
    
    # Build optimized query with only needed fields
    queryset = ScraperJob.objects.only(
        'id', 'scraper_name', 'status', 'started_at', 'completed_at',
        'execution_time', 'jobs_found', 'jobs_new', 'jobs_updated',
        'jobs_duplicate', 'triggered_by', 'created_at'
    )
    
    if scraper_name:
        queryset = queryset.filter(scraper_name=scraper_name)
    if search:
        queryset = queryset.filter(
            Q(scraper_name__icontains=search)
            | Q(status__icontains=search)
            | Q(triggered_by__icontains=search)
            | Q(error_message__icontains=search)
        )
    
    queryset = queryset.order_by('-created_at')
    
    # Paginate results
    paginator = Paginator(queryset, limit)
    paginated_jobs = paginator.get_page(page)
    
    jobs = []
    for job in paginated_jobs.object_list.values(
        'id', 'scraper_name', 'status', 'started_at', 'completed_at',
        'execution_time', 'jobs_found', 'jobs_new', 'jobs_updated',
        'jobs_duplicate', 'triggered_by'
    ):
        if 'id' in job:
            job['id'] = str(job['id'])
        jobs.append(job)
    
    return Response({
        'jobs': jobs,
        'pagination': {
            'page': page,
            'page_size': limit,
            'total': paginator.count,
            'pages': paginator.num_pages
        }
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def scraper_config(request, scraper_name):
    """Get configuration for a specific scraper"""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user
    
    if scraper_name not in list_scrapers():
        return Response(
            {'error': f'Unknown scraper: {scraper_name}'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    site_config = CONFIG['sites'].get(scraper_name, {})
    scraper_config = CONFIG['scrapers'].get(scraper_name, {})
    
    # Get database config if exists
    try:
        db_config = ScraperConfig.objects.get(scraper_name=scraper_name)
        config_data = {
            'name': scraper_name,
            'scraper_name': scraper_name,
            'display_name': site_config.get('name', scraper_name),
            'description': site_config.get('description', ''),
            'is_enabled': db_config.is_enabled,
            'base_url': site_config.get('base_url', ''),
            'max_jobs': db_config.max_jobs,
            'max_pages': db_config.max_pages,
            'timeout': db_config.timeout,
            'retry_count': db_config.retry_count,
            'schedule_enabled': db_config.schedule_enabled,
            'schedule_cron': db_config.schedule_cron,
            'last_run': db_config.last_run,
            'total_runs': db_config.total_runs,
            'successful_runs': db_config.successful_runs,
            'failed_runs': db_config.failed_runs,
            'schedule': _serialize_schedule_snapshot(db_config),
        }
    except ScraperConfig.DoesNotExist:
        config_data = {
            'name': scraper_name,
            'scraper_name': scraper_name,
            'display_name': site_config.get('name', scraper_name),
            'description': site_config.get('description', ''),
            'is_enabled': site_config.get('enabled', False),
            'base_url': site_config.get('base_url', ''),
            'max_jobs': scraper_config.get('max_jobs'),
            'max_pages': scraper_config.get('max_pages'),
            'timeout': 300,
            'retry_count': 3,
            'schedule_enabled': False,
            'schedule_cron': '',
            'last_run': None,
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'schedule': {
                'scraper_name': scraper_name,
                'schedule_enabled': False,
                'schedule_cron': '',
                'task_name': f'scraper_{scraper_name}_managed',
                'celery_beat_available': CELERY_BEAT_AVAILABLE,
                'periodic_task_enabled': False,
                'periodic_task_exists': False,
                'last_run': None,
            },
        }
    
    return Response(config_data)


@api_view(['PUT', 'PATCH'])
@permission_classes([AllowAny])
def update_scraper_config(request, scraper_name):
    """Update scraper configuration"""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user
    
    if scraper_name not in list_scrapers():
        return Response(
            {'error': f'Unknown scraper: {scraper_name}'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get or create config
    config, created = ScraperConfig.objects.get_or_create(
        scraper_name=scraper_name,
        defaults={
            'is_enabled': CONFIG['sites'].get(scraper_name, {}).get('enabled', False),
            'max_jobs': CONFIG['scrapers'].get(scraper_name, {}).get('max_jobs'),
            'max_pages': CONFIG['scrapers'].get(scraper_name, {}).get('max_pages'),
        }
    )
    
    # Update fields
    if 'is_enabled' in request.data:
        config.is_enabled = bool(request.data['is_enabled'])
    if 'enabled' in request.data:
        config.is_enabled = bool(request.data['enabled'])
    if 'max_jobs' in request.data:
        config.max_jobs = request.data['max_jobs'] or None
    if 'max_pages' in request.data:
        config.max_pages = request.data['max_pages'] or None
    if 'timeout' in request.data:
        config.timeout = int(request.data['timeout'])
    if 'retry_count' in request.data:
        config.retry_count = int(request.data['retry_count'])
    if 'schedule_enabled' in request.data:
        config.schedule_enabled = bool(request.data['schedule_enabled'])
    if 'schedule_cron' in request.data:
        config.schedule_cron = (request.data['schedule_cron'] or '').strip()
    if 'description' in request.data:
        config.description = request.data['description'] or ''
    
    config.save()

    try:
        schedule_sync = _sync_scraper_schedule(config)
    except ValueError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({
        'message': 'Configuration updated successfully',
        'scraper_name': scraper_name,
        'is_enabled': config.is_enabled,
        'max_jobs': config.max_jobs,
        'max_pages': config.max_pages,
        'timeout': config.timeout,
        'retry_count': config.retry_count,
        'schedule_enabled': config.schedule_enabled,
        'schedule_cron': config.schedule_cron,
        'schedule_sync': schedule_sync,
    })


@api_view(['DELETE'])
@permission_classes([AllowAny])
def cancel_scraper_job(request, job_id):
    """Cancel a running scraper job"""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user
    
    try:
        job = ScraperJob.objects.get(pk=job_id)
        response_job_id = _job_pk(job)
        
        if job.status in ['completed', 'failed', 'cancelled']:
            return Response(
                {'error': f'Cannot cancel job with status: {job.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        process_stopped = False
        if job.pid:
            try:
                # Use psutil for robust recursive termination
                parent = psutil.Process(job.pid)
                children = parent.children(recursive=True)
                
                # Terminate children first
                for child in children:
                    try:
                        child.terminate()
                    except psutil.NoSuchProcess:
                        pass
                
                # Terminate parent
                parent.terminate()
                
                # Wait for processes to terminate gracefully
                gone, alive = psutil.wait_procs(children + [parent], timeout=3)
                
                # Force kill any survivors
                for p in alive:
                    try:
                        p.kill()
                    except psutil.NoSuchProcess:
                        pass
                
                process_stopped = True
            except psutil.NoSuchProcess:
                logger.warning(f"PID {job.pid} not found for job {job.pk} during cancellation")
                process_stopped = False
            except Exception as e:
                logger.error(f"Error terminating PID {job.pid} for job {job.pk}: {e}")
                # Fallback to simple os.kill
                try:
                    os.kill(job.pid, signal.SIGTERM)
                    process_stopped = True
                except:
                    process_stopped = False

        job.status = 'cancelled'
        job.completed_at = timezone.now()
        job.error_message = 'Cancelled by user'
        job.progress = job.progress or 0
        job.save()
        
        return Response({
            'message': 'Job cancelled successfully',
            'job_id': response_job_id,
            'status': job.status,
            'process_stopped': process_stopped,
        })
        
    except ScraperJob.DoesNotExist:
        return Response(
            {'error': 'Job not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def active_jobs(request):
    """Get list of currently running jobs"""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user
    
    active = ScraperJob.objects.filter(
        status__in=['pending', 'running']
    ).order_by('-started_at')
    
    jobs = []
    for job in active.values(
        'id', 'scraper_name', 'status', 'started_at', 'created_at',
        'parameters', 'triggered_by', 'progress', 'pid', 'jobs_found'
    ):
        if 'id' in job:
            job['id'] = str(job['id'])
        jobs.append(job)
    
    return Response({'active_jobs': jobs, 'count': len(jobs)})


@api_view(['GET'])
@permission_classes([AllowAny])
def recent_jobs(request):
    """Get recently scraped jobs"""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user
    
    limit = int(request.query_params.get('limit', 50))
    source = request.query_params.get('source')
    
    queryset = ScrapedURL.objects.filter(is_active=True)
    if source:
        queryset = queryset.filter(source=source)
    
    jobs = []
    for job in queryset.order_by('-last_scraped')[:limit].values(
        'id', 'job_id', 'url', 'source', 'title', 'company',
        'scrape_count', 'first_scraped', 'last_scraped'
    ):
        if 'id' in job:
            job['id'] = str(job['id'])
        jobs.append(job)
    
    return Response({'jobs': jobs, 'count': len(jobs)})


@api_view(['GET'])
@permission_classes([AllowAny])
def managed_jobs(request):
    """List scraped jobs stored in the main jobs table."""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user

    page = max(int(request.query_params.get('page', 1)), 1)
    limit = min(max(int(request.query_params.get('limit', 20)), 1), 100)
    search = (request.query_params.get('q') or '').strip()
    status_filter = (request.query_params.get('status') or '').strip()
    source_filter = (request.query_params.get('source') or '').strip()
    verified_filter = (request.query_params.get('verified') or 'all').strip().lower()

    queryset = Job.objects.all()
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search)
            | Q(company__icontains=search)
            | Q(location__icontains=search)
            | Q(source__icontains=search)
            | Q(operation_type__icontains=search)
            | Q(job_category__icontains=search)
        )
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if source_filter:
        queryset = queryset.filter(source=source_filter)
    if verified_filter == 'verified':
        queryset = queryset.filter(is_verified=True)
    elif verified_filter == 'unverified':
        queryset = queryset.filter(is_verified=False)

    queryset = queryset.order_by('-retrieved_date', '-created_at')
    paginator = Paginator(queryset, limit)
    page_obj = paginator.get_page(page)

    jobs = []
    for job in page_obj.object_list.values(
        'id', 'title', 'company', 'location', 'source', 'status', 'url',
        'operation_type', 'job_category', 'sub_role', 'country_code',
        'is_verified', 'posted_date', 'retrieved_date', 'description',
        'salary_currency', 'is_remote', 'last_checked'
    ):
        if 'id' in job:
            job['id'] = str(job['id'])
        jobs.append(job)

    return Response({
        'jobs': jobs,
        'pagination': {
            'page': page,
            'page_size': limit,
            'total': paginator.count,
            'pages': paginator.num_pages,
        },
        'summary': _build_job_summary(queryset),
        'sources': sorted(filter(None, Job.objects.exclude(source__isnull=True).values_list('source', flat=True).distinct())),
    })


@api_view(['PATCH', 'DELETE'])
@permission_classes([AllowAny])
def update_managed_job(request, job_id):
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user

    try:
        job = Job.objects.get(pk=job_id)
    except Job.DoesNotExist:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        job_title = job.title
        job.delete()
        return Response({'message': f'Job "{job_title}" deleted successfully', 'job_id': job_id})

    field_names = [
        'title', 'company', 'location', 'status', 'operation_type',
        'job_category', 'sub_role', 'country_code', 'description',
    ]
    for field_name in field_names:
        if field_name in request.data:
            setattr(job, field_name, request.data.get(field_name) or None)

    if 'title' in request.data and request.data.get('title'):
        job.title = request.data['title']
    if 'company' in request.data and request.data.get('company'):
        job.company = request.data['company']
    if 'is_verified' in request.data:
        job.is_verified = bool(request.data['is_verified'])
    if 'is_remote' in request.data:
        job.is_remote = bool(request.data['is_remote'])
    if 'posted_date' in request.data:
        job.posted_date = request.data['posted_date'] or None
    if 'expiration_date' in request.data:
        job.expiration_date = request.data['expiration_date'] or None
    if 'salary_currency' in request.data and request.data.get('salary_currency'):
        job.salary_currency = request.data['salary_currency']

    job.last_checked = timezone.now()
    job.save()

    return Response({
        'message': 'Job updated successfully',
        'job': {
            'id': str(job.pk),
            'title': job.title,
            'company': job.company,
            'location': job.location,
            'source': job.source,
            'status': job.status,
            'url': job.url,
            'operation_type': job.operation_type,
            'job_category': job.job_category,
            'sub_role': job.sub_role,
            'country_code': job.country_code,
            'is_verified': job.is_verified,
            'posted_date': job.posted_date,
            'retrieved_date': job.retrieved_date,
            'description': job.description,
            'salary_currency': job.salary_currency,
            'is_remote': job.is_remote,
            'last_checked': job.last_checked,
        }
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def check_job_url_status(request, job_id):
    """Perform a live check on a job URL to see if it's still active."""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user

    try:
        job = Job.objects.get(pk=job_id)
        if job.is_verified:
            return Response({
                'job_id': str(job.pk),
                'status': job.status,
                'result': 'skipped_verified',
                'message': 'Verified jobs are skipped for automated URL checks.',
            })

        result_payload = _check_job_url(job)
        if result_payload['result'] == 'request_failed':
            return Response({
                'error': f"Request failed: {result_payload['error']}",
                'job_id': str(job.pk),
                'status': job.status,
                'last_checked': job.last_checked
            }, status=status.HTTP_502_BAD_GATEWAY)
        
        return Response({
            'job_id': str(job.pk),
            'status': job.status,
            'last_checked': job.last_checked,
            'result': result_payload['result'],
            'message': f"Job status check completed: {result_payload['result']}"
        })

    except Job.DoesNotExist:
        return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def bulk_check_job_url_status(request):
    """Bulk validate job URLs with guardrails for verified jobs."""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user

    search = (request.data.get('q') or '').strip()
    status_filter = (request.data.get('status') or '').strip()
    source_filter = (request.data.get('source') or '').strip()
    # Enforce platform policy for bulk automated checks:
    # only scraped records are checked, and verified jobs are always skipped.
    only_scraped = True
    skip_verified = True
    max_checks = min(max(int(request.data.get('max_checks', 200)), 1), 500)

    queryset = Job.objects.all()
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search)
            | Q(company__icontains=search)
            | Q(location__icontains=search)
            | Q(source__icontains=search)
            | Q(operation_type__icontains=search)
            | Q(job_category__icontains=search)
        )
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if source_filter:
        queryset = queryset.filter(source=source_filter)
    if only_scraped:
        queryset = queryset.exclude(source__isnull=True).exclude(source='')

    jobs = list(queryset.order_by('-retrieved_date', '-created_at')[:max_checks])
    results = {
        'checked': 0,
        'skipped_verified': 0,
        'skipped_no_url': 0,
        'failed_requests': 0,
        'status_changed': 0,
        'closed_detected': 0,
        'total_candidates': len(jobs),
    }

    for job in jobs:
        if skip_verified and job.is_verified:
            results['skipped_verified'] += 1
            continue

        check_payload = _check_job_url(job)
        if check_payload['result'] == 'skipped_no_url':
            results['skipped_no_url'] += 1
            continue
        if check_payload['result'] == 'request_failed':
            results['failed_requests'] += 1
            continue

        results['checked'] += 1
        if check_payload['status_changed']:
            results['status_changed'] += 1
        if check_payload['status'] == 'closed':
            results['closed_detected'] += 1

    return Response({
        'message': 'Bulk URL validation completed',
        'filters': {
            'q': search,
            'status': status_filter,
            'source': source_filter,
            'only_scraped': only_scraped,
            'skip_verified': skip_verified,
            'max_checks': max_checks,
        },
        'results': results,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def scraped_records(request):
    """Paginated scraped URL records for auditing feed output."""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user

    page = max(int(request.query_params.get('page', 1)), 1)
    limit = min(max(int(request.query_params.get('limit', 20)), 1), 100)
    search = (request.query_params.get('q') or '').strip()
    source = (request.query_params.get('source') or '').strip()

    queryset = ScrapedURL.objects.all()
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search)
            | Q(company__icontains=search)
            | Q(source__icontains=search)
            | Q(url__icontains=search)
        )
    if source:
        queryset = queryset.filter(source=source)

    queryset = queryset.order_by('-last_scraped')
    paginator = Paginator(queryset, limit)
    page_obj = paginator.get_page(page)

    records = list(page_obj.object_list.values(
        'id', 'job_id', 'url', 'source', 'title', 'company',
        'scrape_count', 'is_active', 'first_scraped', 'last_scraped'
    ))

    return Response({
        'records': records,
        'pagination': {
            'page': page,
            'page_size': limit,
            'total': paginator.count,
            'pages': paginator.num_pages,
        },
        'sources': sorted(filter(None, ScrapedURL.objects.values_list('source', flat=True).distinct())),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def scheduler_overview(request):
    """Return scheduling state for scraper configs and beat tasks."""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user

    configs = list(ScraperConfig.objects.order_by('scraper_name'))
    schedules = [_serialize_schedule_snapshot(config) for config in configs]
    active_periodic_tasks = 0
    if CELERY_BEAT_AVAILABLE and PeriodicTask is not None:
        active_periodic_tasks = PeriodicTask.objects.filter(name__startswith='scraper_', enabled=True).count()

    return Response({
        'celery_beat_available': CELERY_BEAT_AVAILABLE,
        'configured_scrapers': len(configs),
        'scheduled_scrapers': sum(1 for item in schedules if item['schedule_enabled']),
        'active_periodic_tasks': active_periodic_tasks,
        'schedules': schedules,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def run_all_scrapers(request):
    """Start all enabled scrapers"""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user
    
    max_jobs = request.data.get('max_jobs')
    max_pages = request.data.get('max_pages')
    job_categories = normalize_job_categories(request.data.get('job_categories'))
    
    # Create job
    scraper_job = ScraperJob.objects.create(
        scraper_name='all',
        status='pending',
        triggered_by=auth_user,
        parameters={
            'max_jobs': max_jobs,
            'max_pages': max_pages,
            'job_categories': job_categories,
        }
    )
    scraper_job_id = _job_pk(scraper_job)
    
    try:
        process_pid = _dispatch_scraper_job(
            'all',
            scraper_job_id,
            max_jobs=max_jobs,
            max_pages=max_pages,
            job_categories=job_categories,
        )
        scraper_job.pid = process_pid
        scraper_job.save(update_fields=['pid'])
        
        return Response({
            'job_id': scraper_job_id,
            'message': 'All scrapers queued',
            'status': 'pending',
            'pid': process_pid,
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        scraper_job.status = 'failed'
        scraper_job.error_message = f"Dispatch failed: {str(e)}"
        scraper_job.save()
        
        return Response(
            {'error': f"Failed to queue job: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint (no authentication required)"""
    
    try:
        # Check database connectivity
        job_count = ScraperJob.objects.count()
        url_count = ScrapedURL.objects.count()
        
        return Response({
            'status': 'healthy',
            'database': 'connected',
            'scrapers_available': len(list_scrapers()),
            'total_jobs': job_count,
            'total_urls': url_count,
        })
    except Exception as e:
        return Response({
            'status': 'unhealthy',
            'error': str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['GET'])
@permission_classes([AllowAny])
def system_metrics(request):
    """Get real-time system metrics (CPU, RAM, Disk)"""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user
        
    try:
        metrics = {
            'cpu': {
                'percent': psutil.cpu_percent(interval=None),
                'count': psutil.cpu_count(),
                'freq': psutil.cpu_freq().current if psutil.cpu_freq() else 0,
            },
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'percent': psutil.virtual_memory().percent,
                'used': psutil.virtual_memory().used,
            },
            'disk': {
                'total': psutil.disk_usage('/').total,
                'used': psutil.disk_usage('/').used,
                'free': psutil.disk_usage('/').free,
                'percent': psutil.disk_usage('/').percent,
            },
            'process': {
                'memory_info': psutil.Process().memory_info().rss,
                'threads': psutil.Process().num_threads(),
            },
            'timestamp': timezone.now().isoformat()
        }
        return Response(metrics)
    except Exception as e:
        logger.error(f"Failed to fetch system metrics: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
