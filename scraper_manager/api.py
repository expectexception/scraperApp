"""
REST API views for scraper management
"""

import logging
import os
import secrets
import subprocess
import sys
import psutil
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.db.models import Count, Avg, Sum
from django.conf import settings
from django.core.cache import cache

from .models import ScraperJob, ScraperConfig, ScrapedURL
from .config import CONFIG
from .scrapers import list_scrapers

# Setup logging
logger = logging.getLogger(__name__)
TOKEN_TTL_SECONDS = 60 * 60 * 12  # 12 hours


def _dashboard_credentials() -> tuple[str, str | None]:
    return (
        getattr(settings, "DASHBOARD_USERNAME", "admin"),
        getattr(settings, "DASHBOARD_PASSWORD", None),
    )


def _issue_dashboard_token(username: str) -> str:
    token = secrets.token_urlsafe(32)
    cache.set(f"dashboard_token:{token}", {"username": username}, TOKEN_TTL_SECONDS)
    return token


def _require_dashboard_auth(request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return Response({"error": "Authorization bearer token required"}, status=status.HTTP_401_UNAUTHORIZED)

    token = auth_header.split(" ", 1)[1].strip()
    token_data = cache.get(f"dashboard_token:{token}")
    if not token_data:
        return Response({"error": "Invalid or expired token"}, status=status.HTTP_401_UNAUTHORIZED)
    return token_data.get("username", "dashboard")


def _dispatch_scraper_job(scraper_name: str, job_id: int, max_jobs=None, max_pages=None):
    """Dispatch scraper command in background without Celery dependency."""
    manage_py = os.path.join(settings.BASE_DIR, "manage.py")
    cmd = [sys.executable, manage_py, "run_scraper", scraper_name, "--job-id", str(job_id)]
    if max_jobs:
        cmd.extend(["--max-jobs", str(max_jobs)])
    if max_pages:
        cmd.extend(["--max-pages", str(max_pages)])
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@api_view(['POST'])
@permission_classes([AllowAny])
def dashboard_login(request):
    """Authenticate dashboard user and return short-lived bearer token."""
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
    scrapers = []
    
    for scraper_name in list_scrapers():
        site_config = CONFIG['sites'].get(scraper_name, {})
        scraper_config = CONFIG['scrapers'].get(scraper_name, {})
        
        scrapers.append({
            'name': scraper_name,
            'display_name': site_config.get('name', scraper_name),
            'description': site_config.get('description', ''),
            'enabled': site_config.get('enabled', False),
            'base_url': site_config.get('base_url', ''),
            'max_jobs': scraper_config.get('max_jobs'),
            'max_pages': scraper_config.get('max_pages'),
        })
    
    return Response({'scrapers': scrapers})


@api_view(['GET'])
@permission_classes([AllowAny])
def scraper_configs(request):
    """Return all scraper configs for dashboard editing."""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user

    configs = {
        cfg.scraper_name: {
            'scraper_name': cfg.scraper_name,
            'is_enabled': cfg.is_enabled,
            'max_jobs': cfg.max_jobs,
            'max_pages': cfg.max_pages,
            'timeout': cfg.timeout,
            'retry_count': cfg.retry_count,
            'schedule_enabled': cfg.schedule_enabled,
            'schedule_cron': cfg.schedule_cron,
            'description': cfg.description,
            'last_run': cfg.last_run,
        }
        for cfg in ScraperConfig.objects.all()
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
        }
    )
    
    logger.info(f"Created ScraperJob {scraper_job.id} for {scraper_name}")
    
    try:
        _dispatch_scraper_job(scraper_name, scraper_job.id, max_jobs=max_jobs, max_pages=max_pages)
        logger.info(f"Dispatched ScraperJob {scraper_job.id} for background execution")
        
        return Response({
            'job_id': scraper_job.id,
            'scraper_name': scraper_name,
            'status': 'pending',
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
        job = ScraperJob.objects.get(id=job_id)
        
        return Response({
            'job_id': job.id,
            'scraper_name': job.scraper_name,
            'status': job.status,
            'started_at': job.started_at,
            'completed_at': job.completed_at,
            'execution_time': job.execution_time,
            'jobs_found': job.jobs_found,
            'jobs_new': job.jobs_new,
            'jobs_updated': job.jobs_updated,
            'jobs_duplicate': job.jobs_duplicate,
            'error_message': job.error_message,
            'output_file': job.output_file,
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
    from django.db.models import Q

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
    }
    
    # Cache for 5 minutes
    cache.set(cache_key, stats_response, 300)
    return Response(stats_response)


@api_view(['GET'])
@permission_classes([AllowAny])
def scraper_history(request):
    """Get scraper execution history with pagination and filtering"""
    from django.core.paginator import Paginator

    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user
    
    scraper_name = request.query_params.get('scraper')
    page = int(request.query_params.get('page', 1))
    limit = int(request.query_params.get('limit', 20))
    
    # Build optimized query with only needed fields
    queryset = ScraperJob.objects.only(
        'id', 'scraper_name', 'status', 'started_at', 'completed_at',
        'execution_time', 'jobs_found', 'jobs_new', 'jobs_updated',
        'jobs_duplicate', 'triggered_by', 'created_at'
    )
    
    if scraper_name:
        queryset = queryset.filter(scraper_name=scraper_name)
    
    queryset = queryset.order_by('-created_at')
    
    # Paginate results
    paginator = Paginator(queryset, limit)
    paginated_jobs = paginator.get_page(page)
    
    jobs = list(paginated_jobs.object_list.values(
        'id', 'scraper_name', 'status', 'started_at', 'completed_at',
        'execution_time', 'jobs_found', 'jobs_new', 'jobs_updated',
        'jobs_duplicate', 'triggered_by'
    ))
    
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
        }
    except ScraperConfig.DoesNotExist:
        config_data = {
            'name': scraper_name,
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
    })


@api_view(['DELETE'])
@permission_classes([AllowAny])
def cancel_scraper_job(request, job_id):
    """Cancel a running scraper job"""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user
    
    try:
        job = ScraperJob.objects.get(id=job_id)
        
        if job.status in ['completed', 'failed', 'cancelled']:
            return Response(
                {'error': f'Cannot cancel job with status: {job.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        job.status = 'cancelled'
        job.completed_at = timezone.now()
        job.error_message = 'Cancelled by user'
        job.save()
        
        return Response({
            'message': 'Job cancelled successfully',
            'job_id': job.id,
            'status': job.status
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
    
    jobs = list(active.values(
        'id', 'scraper_name', 'status', 'started_at',
        'parameters', 'triggered_by'
    ))
    
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
    
    jobs = list(
        queryset.order_by('-last_scraped')[:limit]
        .values(
            'id', 'job_id', 'url', 'source', 'title', 'company',
            'scrape_count', 'first_scraped', 'last_scraped'
        )
    )
    
    return Response({'jobs': jobs, 'count': len(jobs)})


@api_view(['POST'])
@permission_classes([AllowAny])
def run_all_scrapers(request):
    """Start all enabled scrapers"""
    auth_user = _require_dashboard_auth(request)
    if isinstance(auth_user, Response):
        return auth_user
    
    max_jobs = request.data.get('max_jobs')
    max_pages = request.data.get('max_pages')
    
    # Create job
    scraper_job = ScraperJob.objects.create(
        scraper_name='all',
        status='pending',
        triggered_by=auth_user,
        parameters={
            'max_jobs': max_jobs,
            'max_pages': max_pages,
        }
    )
    
    try:
        _dispatch_scraper_job('all', scraper_job.id, max_jobs=max_jobs, max_pages=max_pages)
        
        return Response({
            'job_id': scraper_job.id,
            'message': 'All scrapers queued',
            'status': 'pending'
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
