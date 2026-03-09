"""
Performance Monitoring and Profiling Utilities
Tracks performance metrics for scraper operations
"""

import logging
import time
from functools import wraps
from typing import Callable, Any, Dict, Optional
from django.utils import timezone
from datetime import timedelta
import json

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Tracks performance metrics for different operations"""
    
    _instance = None
    _metrics = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PerformanceMetrics, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def record(cls, operation: str, duration: float, success: bool = True, **metadata):
        """Record a performance metric"""
        if operation not in cls._metrics:
            cls._metrics[operation] = {
                'count': 0,
                'total_time': 0,
                'min_time': float('inf'),
                'max_time': 0,
                'errors': 0,
                'last_recorded': None,
                'samples': []
            }
        
        metric = cls._metrics[operation]
        metric['count'] += 1
        metric['total_time'] += duration
        metric['min_time'] = min(metric['min_time'], duration)
        metric['max_time'] = max(metric['max_time'], duration)
        metric['last_recorded'] = timezone.now().isoformat()
        
        if not success:
            metric['errors'] += 1
        
        # Keep last 10 samples for trend analysis
        metric['samples'].append({
            'duration': duration,
            'success': success,
            'timestamp': timezone.now().isoformat(),
            **metadata
        })
        
        if len(metric['samples']) > 10:
            metric['samples'] = metric['samples'][-10:]
    
    @classmethod
    def get_metrics(cls, operation: Optional[str] = None) -> Dict:
        """Get recorded metrics"""
        if operation:
            if operation not in cls._metrics:
                return {}
            
            metric = cls._metrics[operation]
            return {
                'operation': operation,
                'count': metric['count'],
                'total_time': round(metric['total_time'], 3),
                'avg_time': round(metric['total_time'] / metric['count'], 3),
                'min_time': round(metric['min_time'], 3),
                'max_time': round(metric['max_time'], 3),
                'error_rate': round((metric['errors'] / metric['count'] * 100), 1) if metric['count'] > 0 else 0,
                'last_recorded': metric['last_recorded'],
            }
        
        result = {}
        for op, metric in cls._metrics.items():
            result[op] = {
                'count': metric['count'],
                'avg_time': round(metric['total_time'] / metric['count'], 3),
                'total_time': round(metric['total_time'], 3),
                'error_rate': round((metric['errors'] / metric['count'] * 100), 1) if metric['count'] > 0 else 0,
            }
        
        return result
    
    @classmethod
    def reset(cls, operation: Optional[str] = None):
        """Reset metrics"""
        if operation:
            if operation in cls._metrics:
                del cls._metrics[operation]
        else:
            cls._metrics = {}


class ProfileOperation:
    """Context manager for profiling operations"""
    
    def __init__(self, operation_name: str, log_level: str = 'info', **metadata):
        """
        Initialize profiler
        
        Args:
            operation_name: Name of the operation
            log_level: Logging level (debug, info, warning)
            **metadata: Additional metadata to record
        """
        self.operation_name = operation_name
        self.log_level = log_level
        self.metadata = metadata
        self.start_time = None
        self.duration = None
    
    def __enter__(self):
        self.start_time = time.time()
        logger.debug(f"⏱️  Starting: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = time.time() - self.start_time
        success = exc_type is None
        
        # Record metric
        PerformanceMetrics.record(
            self.operation_name,
            self.duration,
            success=success,
            **self.metadata
        )
        
        # Log result
        status = "✅" if success else "❌"
        log_func = getattr(logger, self.log_level, logger.info)
        
        if success:
            log_func(f"{status} Completed: {self.operation_name} in {self.duration:.3f}s")
        else:
            log_func(f"{status} Failed: {self.operation_name} after {self.duration:.3f}s - {exc_type.__name__}")
        
        return False  # Don't suppress exceptions


def profile_operation(operation_name: str, log_level: str = 'info'):
    """
    Decorator to profile a function's execution time
    
    Args:
        operation_name: Name for the operation
        log_level: Logging level
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            with ProfileOperation(operation_name or func.__name__, log_level):
                return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


class PerformanceAlert:
    """Alerts when operations take longer than expected"""
    
    THRESHOLDS = {
        'api_request': 2.0,  # 2 seconds
        'database_query': 1.0,  # 1 second
        'scraper_run': 300.0,  # 5 minutes
        'batch_insert': 5.0,  # 5 seconds
    }
    
    @staticmethod
    def check_threshold(operation: str, duration: float) -> bool:
        """
        Check if operation exceeded threshold
        
        Returns:
            True if exceeded, False otherwise
        """
        threshold = PerformanceAlert.THRESHOLDS.get(operation, float('inf'))
        
        if duration > threshold:
            logger.warning(
                f"⚠️  Performance Alert: {operation} took {duration:.2f}s "
                f"(threshold: {threshold}s)"
            )
            return True
        
        return False
    
    @staticmethod
    def set_threshold(operation: str, threshold: float):
        """Set custom threshold for an operation"""
        PerformanceAlert.THRESHOLDS[operation] = threshold
        logger.info(f"Set performance threshold for '{operation}' to {threshold}s")


class QueryCounter:
    """Counts database queries in a context"""
    
    def __init__(self, operation_name: str = ""):
        self.operation_name = operation_name
        self.initial_count = None
        self.final_count = None
    
    def __enter__(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        
        self.context = CaptureQueriesContext(connection)
        self.context.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.context.__exit__(exc_type, exc_val, exc_tb)
        
        query_count = len(self.context.captured_queries)
        logger.debug(f"Query count for '{self.operation_name}': {query_count} queries")
        
        # Log slow queries
        for query in self.context.captured_queries:
            duration = float(query.get('time', 0))
            if duration > 0.1:  # More than 100ms
                logger.warning(f"Slow query ({duration:.3f}s): {query['sql'][:100]}...")


def measure_performance(operation_name: str = "", log_slow: bool = True):
    """
    Decorator that measures and logs operation performance
    
    Args:
        operation_name: Name of the operation
        log_slow: Whether to log slow operations as warnings
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Record metric
                PerformanceMetrics.record(op_name, duration, success=True)
                
                # Check threshold
                if log_slow:
                    PerformanceAlert.check_threshold(op_name, duration)
                
                logger.debug(f"✅ {op_name} completed in {duration:.3f}s")
                return result
            
            except Exception as e:
                duration = time.time() - start_time
                PerformanceMetrics.record(op_name, duration, success=False)
                logger.error(f"❌ {op_name} failed after {duration:.3f}s: {str(e)}")
                raise
        
        return wrapper
    
    return decorator


# Helper function to get performance report
def get_performance_report() -> str:
    """Get formatted performance report"""
    metrics = PerformanceMetrics.get_metrics()
    
    if not metrics:
        return "No performance metrics recorded"
    
    report = "📊 Performance Metrics Report\n"
    report += "=" * 60 + "\n"
    
    for operation, stats in sorted(metrics.items()):
        report += f"\n{operation}:\n"
        report += f"  Count: {stats['count']}\n"
        report += f"  Total: {stats['total_time']:.3f}s\n"
        report += f"  Avg: {stats['avg_time']:.3f}s\n"
        report += f"  Min: {stats.get('min_time', 0):.3f}s\n"
        report += f"  Max: {stats.get('max_time', 0):.3f}s\n"
        report += f"  Error Rate: {stats['error_rate']:.1f}%\n"
    
    return report
