"""
Caching Utilities for Scraper Manager
Provides cached access to frequently used data
"""

import logging
import hashlib
from functools import wraps
from typing import Any, Callable
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages caching for scraper operations"""

    # Default cache TTLs (in seconds)
    DEFAULT_TTL = 300  # 5 minutes
    STATS_TTL = 300  # 5 minutes
    CONFIG_TTL = 3600  # 1 hour
    HISTORY_TTL = 600  # 10 minutes

    # Cache key prefixes
    PREFIX_STATS = "scraper:stats"
    PREFIX_CONFIG = "scraper:config"
    PREFIX_HISTORY = "scraper:history"
    PREFIX_JOB = "scraper:job"
    PREFIX_SOURCE = "scraper:source"

    @staticmethod
    def get_cache_key(*args, **kwargs) -> str:
        """Generate a unique cache key from arguments"""
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    @staticmethod
    def cache_result(ttl: int = DEFAULT_TTL, prefix: str = ""):
        """
        Decorator to cache function results

        Args:
            ttl: Time to live in seconds
            prefix: Cache key prefix
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                # Generate cache key
                key_suffix = CacheManager.get_cache_key(*args, **kwargs)
                cache_key = f"{prefix}:{key_suffix}" if prefix else key_suffix

                # Try to get from cache
                result = cache.get(cache_key)
                if result is not None:
                    logger.debug(f"Cache hit for {cache_key}")
                    return result

                # Call function and cache result
                result = func(*args, **kwargs)
                cache.set(cache_key, result, ttl)
                logger.debug(f"Cached result for {cache_key} ({ttl}s)")

                return result

            return wrapper

        return decorator

    @staticmethod
    def invalidate_cache(prefix: str, *args, **kwargs) -> None:
        """
        Invalidate cache entries matching pattern

        Args:
            prefix: Cache key prefix
            *args: Arguments used to generate specific key
            **kwargs: Keyword arguments used to generate specific key
        """
        if args or kwargs:
            # Invalidate specific key
            key_suffix = CacheManager.get_cache_key(*args, **kwargs)
            cache_key = f"{prefix}:{key_suffix}"
            cache.delete(cache_key)
            logger.debug(f"Invalidated cache key: {cache_key}")
        else:
            # Invalidate all keys with prefix
            # Note: Django cache doesn't have prefix-based deletion for all backends
            # This is a limitation - you may need to use cache.clear() for memcached
            logger.warning(
                f"Prefix-based cache invalidation not fully supported: {prefix}"
            )

    @staticmethod
    def get_scraper_stats(fresh: bool = False) -> dict:
        """Get cached scraper statistics"""
        from .models import ScraperJob
        from django.db.models import Count, Avg, Sum, Q

        cache_key = f"{CacheManager.PREFIX_STATS}:summary"

        if not fresh:
            result = cache.get(cache_key)
            if result is not None:
                return result

        # Calculate fresh stats
        stats = ScraperJob.objects.aggregate(
            total_runs=Count("id"),
            completed_runs=Count("id", filter=Q(status="completed")),
            failed_runs=Count("id", filter=Q(status="failed")),
            running_runs=Count("id", filter=Q(status="running")),
            avg_time=Avg(
                "execution_time",
                filter=Q(status="completed", execution_time__isnull=False),
            ),
            total_new=Sum("jobs_new"),
            total_found=Sum("jobs_found"),
            total_updated=Sum("jobs_updated"),
        )

        result = {
            "total_runs": stats["total_runs"] or 0,
            "completed_runs": stats["completed_runs"] or 0,
            "failed_runs": stats["failed_runs"] or 0,
            "running_runs": stats["running_runs"] or 0,
            "avg_execution_time": round(stats["avg_time"] or 0, 2),
            "total_jobs_found": stats["total_found"] or 0,
            "total_new_jobs": stats["total_new"] or 0,
            "total_updated_jobs": stats["total_updated"] or 0,
            "success_rate": (stats["completed_runs"] / stats["total_runs"] * 100)
            if stats["total_runs"] > 0
            else 0,
            "cached_at": timezone.now().isoformat(),
        }

        cache.set(cache_key, result, CacheManager.STATS_TTL)
        return result

    @staticmethod
    def get_scraper_config(scraper_name: str, fresh: bool = False) -> dict:
        """Get cached scraper configuration"""
        from .models import ScraperConfig
        from .config import CONFIG

        cache_key = f"{CacheManager.PREFIX_CONFIG}:{scraper_name}"

        if not fresh:
            result = cache.get(cache_key)
            if result is not None:
                return result

        # Get from database
        try:
            db_config = ScraperConfig.objects.get(scraper_name=scraper_name)
            site_config = CONFIG["sites"].get(scraper_name, {})

            result = {
                "name": scraper_name,
                "display_name": site_config.get("name", scraper_name),
                "description": site_config.get("description", ""),
                "enabled": db_config.is_enabled,
                "base_url": site_config.get("base_url", ""),
                "max_jobs": db_config.max_jobs,
                "max_pages": db_config.max_pages,
            }
        except (ScraperConfig.DoesNotExist, Exception) as e:
            # Fallback to config file
            site_config = CONFIG["sites"].get(scraper_name, {})
            scraper_config = CONFIG["scrapers"].get(scraper_name, {})

            result = {
                "name": scraper_name,
                "display_name": site_config.get("name", scraper_name),
                "description": site_config.get("description", ""),
                "enabled": site_config.get("enabled", False),
                "base_url": site_config.get("base_url", ""),
                "max_jobs": scraper_config.get("max_jobs"),
                "max_pages": scraper_config.get("max_pages"),
            }
            if not isinstance(e, ScraperConfig.DoesNotExist):
                logger.error(f"Error getting scraper config for {scraper_name}: {e}")

        cache.set(cache_key, result, CacheManager.CONFIG_TTL)
        return result

    @staticmethod
    def get_job_stats_by_source(fresh: bool = False) -> dict:
        """Get cached job statistics by source"""
        from .models import ScrapedURL
        from django.db.models import Count

        cache_key = f"{CacheManager.PREFIX_SOURCE}:stats"

        if not fresh:
            result = cache.get(cache_key)
            if result is not None:
                return result

        # Calculate fresh stats
        stats = dict(
            ScrapedURL.objects.values("source")
            .annotate(count=Count("id"))
            .values_list("source", "count")
        )

        result = {
            "by_source": stats,
            "total": sum(stats.values()),
            "cached_at": timezone.now().isoformat(),
        }

        cache.set(cache_key, result, CacheManager.STATS_TTL)
        return result

    @staticmethod
    def invalidate_all_stats() -> None:
        """Invalidate all statistics caches"""
        cache_keys = [
            f"{CacheManager.PREFIX_STATS}:summary",
            f"{CacheManager.PREFIX_SOURCE}:stats",
        ]

        for key in cache_keys:
            cache.delete(key)

        logger.info("Invalidated all statistics caches")

    @staticmethod
    def invalidate_config(scraper_name: str) -> None:
        """Invalidate scraper configuration cache"""
        cache_key = f"{CacheManager.PREFIX_CONFIG}:{scraper_name}"
        cache.delete(cache_key)
        logger.debug(f"Invalidated config cache for {scraper_name}")


def cache_results(ttl: int = 300):
    """Convenience decorator for caching function results"""
    return CacheManager.cache_result(ttl=ttl)
