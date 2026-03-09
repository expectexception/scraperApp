"""
Serializers for scraper_manager app
"""

from rest_framework import serializers
from .models import ScraperJob, ScraperConfig, ScrapedURL


class ScraperJobSerializer(serializers.ModelSerializer):
    """Serializer for ScraperJob model"""
    
    duration = serializers.SerializerMethodField()
    success_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = ScraperJob
        fields = [
            'id', 'scraper_name', 'status', 'started_at', 'completed_at',
            'execution_time', 'duration', 'jobs_found', 'jobs_new',
            'jobs_updated', 'jobs_duplicate', 'error_message', 'output_file',
            'triggered_by', 'parameters', 'created_at', 'success_rate'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_duration(self, obj):
        """Get human-readable duration"""
        if obj.execution_time:
            if obj.execution_time < 60:
                return f"{obj.execution_time:.1f}s"
            else:
                minutes = int(obj.execution_time // 60)
                seconds = int(obj.execution_time % 60)
                return f"{minutes}m {seconds}s"
        return None
    
    def get_success_rate(self, obj):
        """Calculate success rate"""
        if obj.jobs_found and obj.jobs_found > 0:
            return round((obj.jobs_new / obj.jobs_found) * 100, 1)
        return 0


class ScraperConfigSerializer(serializers.ModelSerializer):
    """Serializer for ScraperConfig model"""
    
    success_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = ScraperConfig
        fields = [
            'id', 'scraper_name', 'enabled', 'max_jobs', 'max_pages',
            'schedule', 'last_run', 'total_runs', 'successful_runs',
            'failed_runs', 'total_jobs_found', 'success_rate', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'last_run', 'total_runs',
                           'successful_runs', 'failed_runs', 'total_jobs_found']
    
    def get_success_rate(self, obj):
        """Calculate success rate"""
        if obj.total_runs > 0:
            return round((obj.successful_runs / obj.total_runs) * 100, 1)
        return 0


class ScrapedURLSerializer(serializers.ModelSerializer):
    """Serializer for ScrapedURL model"""
    
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = ScrapedURL
        fields = [
            'id', 'url', 'job_id', 'source', 'title', 'company',
            'scrape_count', 'is_active', 'first_scraped', 'last_scraped',
            'age', 'job_data'
        ]
        read_only_fields = ['id', 'first_scraped', 'last_scraped']
    
    def get_age(self, obj):
        """Get age in days since first scraped"""
        from django.utils import timezone
        delta = timezone.now() - obj.first_scraped
        return delta.days


class ScraperListSerializer(serializers.Serializer):
    """Serializer for scraper list"""
    
    name = serializers.CharField()
    display_name = serializers.CharField()
    description = serializers.CharField()
    enabled = serializers.BooleanField()
    base_url = serializers.CharField()
    max_jobs = serializers.IntegerField(allow_null=True)
    max_pages = serializers.IntegerField(allow_null=True)
    last_run = serializers.DateTimeField(allow_null=True, required=False)
    total_runs = serializers.IntegerField(default=0, required=False)
    status = serializers.CharField(default='idle', required=False)


class StartScraperSerializer(serializers.Serializer):
    """Serializer for starting a scraper"""
    
    scraper_name = serializers.CharField(required=True)
    max_jobs = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    max_pages = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    
    def validate_scraper_name(self, value):
        """Validate scraper name"""
        from .scrapers import list_scrapers
        if value not in list_scrapers() and value != 'all':
            raise serializers.ValidationError(f"Unknown scraper: {value}")
        return value


class ScraperStatsSerializer(serializers.Serializer):
    """Serializer for scraper statistics"""
    
    total_runs = serializers.IntegerField()
    completed_runs = serializers.IntegerField()
    failed_runs = serializers.IntegerField()
    success_rate = serializers.FloatField()
    total_jobs_scraped = serializers.IntegerField()
    jobs_by_source = serializers.DictField()
    avg_execution_time = serializers.FloatField()
    recent_jobs = serializers.ListField()
