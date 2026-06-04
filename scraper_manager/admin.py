from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.core.management import call_command
from django.db.models import Count, Avg, Sum
from django.utils import timezone
from datetime import timedelta
from .models import ScraperJob, ScraperConfig, ScrapedURL

# For linking companies if a mapping exists
# CompanyMapping is imported inside `get_company` to avoid circular import issues
import threading
import json
import logging

logger = logging.getLogger(__name__)

# Import custom admin site
from backendMain.admin import admin_site

# Import Celery Beat models for scheduling
try:
    from django_celery_beat.models import (
        PeriodicTask,
        CrontabSchedule,
        IntervalSchedule,
    )

    CELERY_BEAT_AVAILABLE = True
except ImportError:
    CELERY_BEAT_AVAILABLE = False
    logger.warning("django_celery_beat not installed - scheduling features disabled")


@admin.register(ScraperJob, site=admin_site)
class ScraperJobAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "get_scraper_display",
        "get_status_badge",
        "get_results",
        "get_duration",
        "get_performance",
        "triggered_by",
        "created_at",
    ]
    list_filter = ["status", "scraper_name", "created_at", "triggered_by"]
    search_fields = ["scraper_name", "triggered_by", "error_message", "id"]
    readonly_fields = [
        "created_at",
        "started_at",
        "completed_at",
        "execution_time",
        "duration",
        "get_job_details",
    ]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    actions = ["cancel_jobs", "retry_failed_jobs", "delete_old_jobs"]
    list_per_page = 50
    show_full_result_count = True
    list_select_related = True

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "trigger-scraper/",
                self.admin_site.admin_view(self.trigger_scraper_view),
                name="trigger_scraper",
            ),
            path(
                "dashboard/",
                self.admin_site.admin_view(self.dashboard_view),
                name="scraper_dashboard",
            ),
            path(
                "api/stats/",
                self.admin_site.admin_view(self.stats_api),
                name="stats_api",
            ),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        """Analytics dashboard with charts and insights"""
        now = timezone.now()

        # Overall statistics
        total_jobs = ScraperJob.objects.count()
        completed = ScraperJob.objects.filter(status="completed").count()
        success_rate = (completed / total_jobs * 100) if total_jobs > 0 else 0

        # Last 7 days data
        daily_stats = []
        for i in range(7):
            day = now - timedelta(days=6 - i)
            day_start = day.replace(hour=0, minute=0, second=0)
            day_end = day.replace(hour=23, minute=59, second=59)

            jobs = ScraperJob.objects.filter(
                created_at__gte=day_start, created_at__lte=day_end
            )

            daily_stats.append(
                {
                    "date": day.strftime("%m/%d"),
                    "total": jobs.count(),
                    "completed": jobs.filter(status="completed").count(),
                    "failed": jobs.filter(status="failed").count(),
                }
            )

        # Scraper performance
        scraper_stats = (
            ScraperJob.objects.filter(status="completed")
            .values("scraper_name")
            .annotate(
                total=Count("id"),
                avg_duration=Avg("execution_time"),
                total_jobs_found=Sum("jobs_found"),
                total_new=Sum("jobs_new"),
            )
            .order_by("-total")
        )

        context = {
            **self.admin_site.each_context(request),
            "title": "Scraper Analytics Dashboard",
            "total_jobs": total_jobs,
            "success_rate": success_rate,
            "daily_stats": json.dumps(daily_stats),
            "scraper_stats": scraper_stats,
            "total_urls": ScrapedURL.objects.count(),
            "active_urls": ScrapedURL.objects.filter(is_active=True).count(),
        }
        return render(request, "admin/scraper_manager/dashboard.html", context)

    def stats_api(self, request):
        """API endpoint for overall statistics"""
        now = timezone.now()
        stats = {
            "total_jobs": ScraperJob.objects.count(),
            "running": ScraperJob.objects.filter(status="running").count(),
            "completed": ScraperJob.objects.filter(status="completed").count(),
            "failed": ScraperJob.objects.filter(status="failed").count(),
            "pending": ScraperJob.objects.filter(status="pending").count(),
            "completed_today": ScraperJob.objects.filter(
                status="completed", completed_at__gte=now - timedelta(days=1)
            ).count(),
            "total_urls": ScrapedURL.objects.count(),
            "enabled_scrapers": ScraperConfig.objects.filter(is_enabled=True).count(),
            "avg_duration": ScraperJob.objects.filter(
                status="completed", execution_time__isnull=False
            ).aggregate(avg=Avg("execution_time"))["avg"]
            or 0,
        }
        return JsonResponse(stats)

    def trigger_scraper_view(self, request):
        """Custom view to trigger scrapers manually"""
        # Check for immediate run (GET with immediate=true) or form submission (POST)
        if request.method == "POST" or (
            request.method == "GET" and request.GET.get("immediate") == "true"
        ):
            # Get params from POST or GET
            scraper_name = request.POST.get("scraper_name") or request.GET.get(
                "scraper_name"
            )
            max_jobs = request.POST.get("max_jobs")

            # Validate inputs
            if not scraper_name:
                messages.error(request, "Please select a scraper")
                return redirect("admin:trigger_scraper")

            # Convert to integers if provided (only applies to POST usually)
            try:
                max_jobs = int(max_jobs) if max_jobs else None
            except ValueError:
                messages.error(request, "Invalid number format")
                return redirect("admin:trigger_scraper")

            # Create job record
            job = ScraperJob.objects.create(
                scraper_name=scraper_name,
                status="pending",
                triggered_by=request.user.username,
                parameters={
                    "max_jobs": max_jobs,
                },
            )

            # Run scraper in background thread
            def run_scraper():
                args = [scraper_name]
                kwargs = {}
                if max_jobs:
                    kwargs["max_jobs"] = max_jobs

                try:
                    call_command("run_scraper", *args, **kwargs)
                except Exception as e:
                    logger.error(
                        f"Error running scraper {scraper_name}: {str(e)}", exc_info=True
                    )

            thread = threading.Thread(target=run_scraper)
            thread.daemon = True
            thread.start()

            messages.success(
                request,
                f'✅ Scraper "{scraper_name}" started successfully! Job ID: {job.id}',
            )
            return redirect("admin:scraper_manager_scraperjob_changelist")

        # GET request without immediate flag - show form
        from .scrapers import list_scrapers
        from .config import CONFIG

        scrapers_list = []
        for scraper_name in list_scrapers():
            site_config = CONFIG["sites"].get(scraper_name, {})
            scraper_limits = CONFIG["scrapers"].get(scraper_name, {})

            # Sync Config to DB (Get or Create)
            defaults = {
                "is_enabled": site_config.get("enabled", True),
                "description": site_config.get("description", ""),
                "max_jobs": scraper_limits.get("max_jobs"),
            }

            config, created = ScraperConfig.objects.get_or_create(
                scraper_name=scraper_name, defaults=defaults
            )

            scrapers_list.append(
                {
                    "name": scraper_name,
                    "display_name": site_config.get("name", scraper_name),
                    "enabled": config.is_enabled,  # Source of Truth: DB
                    "description": config.description,  # Source of Truth: DB
                    "max_jobs": config.max_jobs,
                }
            )

        context = {
            **self.admin_site.each_context(request),
            "title": "Trigger Scraper Manually",
            "scrapers": scrapers_list,
            "opts": self.model._meta,
            "initial_scraper": request.GET.get("scraper_name"),
        }
        return render(request, "admin/scraper_manager/trigger_scraper.html", context)

    def cancel_jobs(self, request, queryset):
        """Cancel selected jobs"""
        updated = 0
        for job in queryset.filter(status__in=["pending", "running"]):
            job.status = "cancelled"
            job.error_message = "Cancelled by admin"
            job.save()
            updated += 1

        if updated:
            self.message_user(
                request, f"{updated} job(s) cancelled successfully", messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                "No jobs were cancelled (only pending/running jobs can be cancelled)",
                messages.WARNING,
            )

    cancel_jobs.short_description = "❌ Cancel selected jobs"

    def changelist_view(self, request, extra_context=None):
        """Add custom dashboard and statistics to changelist"""
        extra_context = extra_context or {}
        extra_context["trigger_scraper_url"] = reverse("admin:trigger_scraper")
        extra_context["dashboard_url"] = reverse("admin:scraper_dashboard")

        # Add quick stats
        now = timezone.now()
        stats = {
            "total_jobs": ScraperJob.objects.count(),
            "running": ScraperJob.objects.filter(status="running").count(),
            "completed_today": ScraperJob.objects.filter(
                status="completed", completed_at__gte=now - timedelta(days=1)
            ).count(),
            "total_urls": ScrapedURL.objects.count(),
        }
        extra_context["quick_stats"] = stats

        return super().changelist_view(request, extra_context)

    class Media:
        css = {"all": ("admin/css/scraper_admin.css",)}
        js = ("admin/js/scraper_admin.js",)

    fieldsets = (
        (
            "Job Information",
            {"fields": ("scraper_name", "status", "triggered_by", "parameters")},
        ),
        (
            "Timing",
            {"fields": ("started_at", "completed_at", "execution_time", "duration")},
        ),
        (
            "Results",
            {"fields": ("jobs_found", "jobs_new", "jobs_updated", "jobs_duplicate")},
        ),
        ("Output", {"fields": ("output_file", "error_message")}),
        ("Details", {"fields": ("get_job_details",), "classes": ("collapse",)}),
    )

    def get_scraper_display(self, obj):
        icons = {
            "signature": "✈️",
            "flygosh": "🛫",
            "aap": "🛩️",
            "aviationjobsearch": "🔍",
            "goose": "🦆",
            "all": "🌐",
        }
        icon = icons.get(obj.scraper_name, "🔧")
        return format_html(
            '<span style="font-weight: bold;">{} {}</span>', icon, obj.scraper_name
        )

    get_scraper_display.short_description = "Scraper"
    get_scraper_display.admin_order_field = "scraper_name"

    def get_status_badge(self, obj):
        colors = {
            "pending": ("#ffc107", "⏳"),
            "running": ("#0066cc", "▶️"),
            "completed": ("#28a745", "✓"),
            "failed": ("#dc3545", "✗"),
        }
        color, icon = colors.get(obj.status, ("#6c757d", "?"))
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 10px; border-radius: 10px; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.status.upper(),
        )

    get_status_badge.short_description = "Status"
    get_status_badge.admin_order_field = "status"

    def get_results(self, obj):
        if obj.status == "completed":
            return format_html(
                '<span style="color: #0066cc;">📊 {}</span> | '
                '<span style="color: #28a745;">✨ {}</span> | '
                '<span style="color: #fd7e14;">↻ {}</span>',
                obj.jobs_found,
                obj.jobs_new,
                obj.jobs_updated,
            )
        return "-"

    get_results.short_description = "Results (Found | New | Updated)"

    def get_duration(self, obj):
        if obj.execution_time:
            return format_html(
                '<span style="font-weight: bold;">{}s</span>', int(obj.execution_time)
            )
        return "-"

    get_duration.short_description = "Duration"

    def get_performance(self, obj):
        """Calculate and display performance metrics"""
        if obj.status == "completed" and obj.execution_time and obj.jobs_found:
            rate = (
                float(obj.jobs_found) / float(obj.execution_time)
                if obj.execution_time > 0
                else 0
            )
            efficiency = (
                (float(obj.jobs_new) / float(obj.jobs_found) * 100)
                if obj.jobs_found > 0
                else 0
            )

            color = (
                "#28a745"
                if efficiency >= 50
                else "#fd7e14"
                if efficiency >= 20
                else "#dc3545"
            )
            rate_str = f"{rate:.1f}"
            efficiency_str = f"{efficiency:.0f}"

            return format_html(
                '<span style="font-size: 11px;">{} jobs/s<br/>'
                '<span style="color: {}; font-weight: bold;">{}% new</span></span>',
                rate_str,
                color,
                efficiency_str,
            )
        return "-"

    get_performance.short_description = "Performance"

    def retry_failed_jobs(self, request, queryset):
        """Retry failed jobs"""
        failed_jobs = queryset.filter(status="failed")
        count = 0
        for job in failed_jobs:
            ScraperJob.objects.create(
                scraper_name=job.scraper_name,
                status="pending",
                triggered_by=f"{request.user.username} (retry)",
                parameters=job.parameters,
            )

            # Run in background
            def run_scraper(scraper_name, params):
                args = [scraper_name]
                kwargs = {}
                if params.get("max_jobs"):
                    kwargs["max_jobs"] = params["max_jobs"]
                try:
                    call_command("run_scraper", *args, **kwargs)
                except Exception as e:
                    logger.error(
                        f"Error retrying scraper {scraper_name}: {str(e)}",
                        exc_info=True,
                    )

            thread = threading.Thread(
                target=run_scraper, args=(job.scraper_name, job.parameters)
            )
            thread.daemon = True
            thread.start()
            count += 1

        if count:
            self.message_user(
                request, f"✅ Retrying {count} failed job(s)", messages.SUCCESS
            )
        else:
            self.message_user(request, "No failed jobs selected", messages.WARNING)

    retry_failed_jobs.short_description = "🔄 Retry failed jobs"

    def delete_old_jobs(self, request, queryset):
        """Delete jobs older than 30 days"""
        from datetime import timedelta
        from django.utils import timezone

        thirty_days_ago = timezone.now() - timedelta(days=30)
        old_jobs = queryset.filter(created_at__lt=thirty_days_ago)
        count = old_jobs.count()

        if count > 0:
            old_jobs.delete()
            self.message_user(
                request, f"🗑️ Deleted {count} old job(s)", messages.SUCCESS
            )
        else:
            self.message_user(
                request, "No jobs older than 30 days found", messages.INFO
            )

    delete_old_jobs.short_description = "🗑️ Delete old jobs (>30 days)"

    def get_job_details(self, obj):
        html = f"""
        <div style="border: 2px solid #ddd; padding: 15px; border-radius: 8px;">
            <h3>Job Execution Details</h3>
            <table style="width: 100%;">
                <tr><td><strong>Status:</strong></td><td>{obj.get_status_display()}</td></tr>
                <tr><td><strong>Started:</strong></td><td>{obj.started_at or "N/A"}</td></tr>
                <tr><td><strong>Completed:</strong></td><td>{obj.completed_at or "N/A"}</td></tr>
                <tr><td><strong>Jobs Found:</strong></td><td>{obj.jobs_found}</td></tr>
                <tr><td><strong>New:</strong></td><td>{obj.jobs_new}</td></tr>
                <tr><td><strong>Updated:</strong></td><td>{obj.jobs_updated}</td></tr>
                <tr><td><strong>Duplicates:</strong></td><td>{obj.jobs_duplicate}</td></tr>
            </table>
        </div>
        """
        return format_html(html)

    get_job_details.short_description = "Job Details"


@admin.register(ScraperConfig, site=admin_site)
class ScraperConfigAdmin(admin.ModelAdmin):
    list_display = [
        "get_scraper_icon",
        "scraper_name",
        "get_enabled_badge",
        "get_limits",
        "last_run",
        "get_statistics",
        "get_success_rate",
        "get_schedule_status",
        "action_buttons",
    ]
    list_filter = ["is_enabled", "schedule_enabled"]
    search_fields = ["scraper_name", "description"]
    actions = [
        "enable_scrapers",
        "disable_scrapers",
        "run_selected_scrapers",
        "setup_daily_schedule",
        "disable_schedules",
    ]
    readonly_fields = ["last_run", "total_runs", "successful_runs", "failed_runs"]
    list_per_page = 20

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "schedule-manager/",
                self.admin_site.admin_view(self.schedule_manager_view),
                name="scraper_schedule_manager",
            ),
        ]
        return custom_urls + urls

    def schedule_manager_view(self, request):
        """Central schedule management interface"""
        if not CELERY_BEAT_AVAILABLE:
            messages.error(
                request, "Celery Beat is not installed. Cannot manage schedules."
            )
            return redirect("admin:index")

        # Get all scrapers with their schedules
        scrapers_with_schedules = []
        for config in ScraperConfig.objects.all():
            task_name = f"scraper_{config.scraper_name}_daily"
            periodic_task = PeriodicTask.objects.filter(name=task_name).first()

            scrapers_with_schedules.append(
                {
                    "config": config,
                    "periodic_task": periodic_task,
                    "has_schedule": periodic_task is not None,
                    "schedule_enabled": periodic_task.enabled
                    if periodic_task
                    else False,
                }
            )

        context = {
            **self.admin_site.each_context(request),
            "title": "Scraper Schedule Manager",
            "scrapers": scrapers_with_schedules,
            "celery_beat_available": CELERY_BEAT_AVAILABLE,
            "opts": self.model._meta,
        }

        return render(request, "admin/scraper_manager/schedule_manager.html", context)

    def setup_daily_schedule(self, request, queryset):
        """Set up daily schedule at midnight for selected scrapers"""
        if not CELERY_BEAT_AVAILABLE:
            self.message_user(request, "Celery Beat is not available", messages.ERROR)
            return

        # Get or create midnight schedule (00:00)
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute="0",
            hour="0",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
        )

        count = 0
        for config in queryset:
            task_name = f"scraper_{config.scraper_name}_daily"

            # Create or update periodic task
            task, created = PeriodicTask.objects.update_or_create(
                name=task_name,
                defaults={
                    "task": "scraper_manager.run_single_scraper",
                    "crontab": schedule,
                    "enabled": config.is_enabled,
                    "kwargs": json.dumps(
                        {
                            "scraper_name": config.scraper_name,
                            "max_jobs": config.max_jobs,
                        }
                    ),
                    "description": f"Daily scrape for {config.scraper_name} at midnight",
                },
            )

            config.schedule_enabled = True
            config.schedule_cron = "0 0 * * *"
            config.save(update_fields=["schedule_enabled", "schedule_cron"])

            count += 1

        self.message_user(
            request,
            f"✅ Set up daily midnight schedule for {count} scraper(s)",
            messages.SUCCESS,
        )

    setup_daily_schedule.short_description = "🕐 Set up daily schedule (midnight UTC)"

    def disable_schedules(self, request, queryset):
        """Disable schedules for selected scrapers"""
        if not CELERY_BEAT_AVAILABLE:
            self.message_user(request, "Celery Beat is not available", messages.ERROR)
            return

        count = 0
        for config in queryset:
            task_name = f"scraper_{config.scraper_name}_daily"

            # Disable or delete the periodic task
            tasks = PeriodicTask.objects.filter(name=task_name)
            tasks.update(enabled=False)

            config.schedule_enabled = False
            config.save(update_fields=["schedule_enabled"])

            count += 1

        self.message_user(
            request, f"⏸️ Disabled schedules for {count} scraper(s)", messages.SUCCESS
        )

    disable_schedules.short_description = "⏸️ Disable schedules"

    def get_schedule_status(self, obj):
        """Show if scraper has an active schedule"""
        if not CELERY_BEAT_AVAILABLE:
            return "-"

        if not obj.schedule_enabled:
            return format_html(
                '<span style="color: #999; font-size: 11px;">No schedule</span>'
            )

        task_name = f"scraper_{obj.scraper_name}_daily"
        periodic_task = PeriodicTask.objects.filter(name=task_name).first()

        if periodic_task and periodic_task.enabled:
            schedule_text = obj.schedule_cron or "Daily"
            return format_html(
                '<span style="background: #10b981; color: white; padding: 3px 8px; border-radius: 4px; font-size: 10px;">⏰ {}</span>',
                schedule_text,
            )
        else:
            return format_html(
                '<span style="background: #94a3b8; color: white; padding: 3px 8px; border-radius: 4px; font-size: 10px;">⏸️ Paused</span>'
            )

    get_schedule_status.short_description = "Schedule"

    fieldsets = (
        ("Basic Settings", {"fields": ("scraper_name", "is_enabled")}),
        (
            "Limits",
            {
                "fields": ("max_jobs",),
                "description": "Set limits for scraping operations (leave blank for unlimited)",
            },
        ),
        (
            "Scheduling",
            {
                "fields": ("schedule_enabled", "schedule_cron"),
                "description": "Configure automated scheduling (requires Celery Beat)",
            },
        ),
        (
            "Statistics",
            {
                "fields": ("last_run", "total_runs", "successful_runs", "failed_runs"),
                "classes": ("collapse",),
            },
        ),
    )

    def action_buttons(self, obj):
        """Action buttons for each scraper"""
        return format_html(
            '<a class="button" href="{}?scraper_name={}&immediate=true" style="background: #417690; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none;">▶️ Run Now</a>',
            reverse("admin:trigger_scraper"),
            obj.scraper_name,
        )

    action_buttons.short_description = "Actions"

    def get_scraper_icon(self, obj):
        """Display scraper with appropriate icon"""
        icons = {
            "signature": "✈️",
            "flygosh": "🛫",
            "aap": "🛩️",
            "aviationjobsearch": "🔍",
            "goose": "🦆",
            "aviationindeed": "📋",
            "indigo": "🔷",
        }
        icon = icons.get(obj.scraper_name, "🔧")
        return format_html('<span style="font-size: 20px;">{}</span>', icon)

    get_scraper_icon.short_description = ""

    def get_limits(self, obj):
        """Display configured limits"""
        jobs_text = f"{obj.max_jobs} jobs" if obj.max_jobs else "∞ jobs"
        return format_html('<span style="font-size: 11px;">{}</span>', jobs_text)

    get_limits.short_description = "Limits"

    def get_statistics(self, obj):
        """Display run statistics"""
        if obj.total_runs > 0:
            return format_html(
                '<span style="font-size: 11px;">'
                "📊 {} runs<br/>"
                '<span style="color: #28a745;">✓ {}</span> / '
                '<span style="color: #dc3545;">✗ {}</span>'
                "</span>",
                obj.total_runs,
                obj.successful_runs,
                obj.failed_runs,
            )
        return format_html(
            '<span style="color: #999; font-size: 11px;">No runs yet</span>'
        )

    get_statistics.short_description = "Stats"

    def enable_scrapers(self, request, queryset):
        """Enable selected scrapers"""
        updated = queryset.update(is_enabled=True)
        self.message_user(
            request, f"{updated} scraper(s) enabled successfully", messages.SUCCESS
        )

    enable_scrapers.short_description = "✅ Enable selected scrapers"

    def disable_scrapers(self, request, queryset):
        """Disable selected scrapers"""
        updated = queryset.update(is_enabled=False)
        self.message_user(
            request, f"{updated} scraper(s) disabled successfully", messages.SUCCESS
        )

    disable_scrapers.short_description = "❌ Disable selected scrapers"

    def run_selected_scrapers(self, request, queryset):
        """Run selected scrapers"""
        count = 0
        for config in queryset.filter(is_enabled=True):
            ScraperJob.objects.create(
                scraper_name=config.scraper_name,
                status="pending",
                triggered_by=request.user.username,
                parameters={
                    "max_jobs": config.max_jobs,
                },
            )

            # Run in background
            def run_scraper(scraper_name, max_jobs):
                args = [scraper_name]
                kwargs = {}
                if max_jobs:
                    kwargs["max_jobs"] = max_jobs
                call_command("run_scraper", *args, **kwargs)

            thread = threading.Thread(
                target=run_scraper, args=(config.scraper_name, config.max_jobs)
            )
            thread.daemon = True
            thread.start()
            count += 1

        if count:
            self.message_user(
                request, f"✅ Started {count} scraper(s)", messages.SUCCESS
            )
        else:
            self.message_user(request, "No enabled scrapers selected", messages.WARNING)

    run_selected_scrapers.short_description = "🚀 Run selected scrapers now"

    def changelist_view(self, request, extra_context=None):
        """Add schedule manager link to changelist"""
        extra_context = extra_context or {}
        extra_context["schedule_manager_url"] = reverse(
            "admin:scraper_schedule_manager"
        )
        extra_context["celery_beat_available"] = CELERY_BEAT_AVAILABLE

        # Quick schedule stats
        if CELERY_BEAT_AVAILABLE:
            scheduled_count = PeriodicTask.objects.filter(
                name__startswith="scraper_", enabled=True
            ).count()
            extra_context["scheduled_scrapers"] = scheduled_count

        return super().changelist_view(request, extra_context)

    def get_enabled_badge(self, obj):
        if obj.is_enabled:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 4px 10px; border-radius: 10px; font-weight: bold;">✓ ON</span>'
            )
        return format_html(
            '<span style="background: #dc3545; color: white; padding: 4px 10px; border-radius: 10px; font-weight: bold;">✗ OFF</span>'
        )

    get_enabled_badge.short_description = "Status"

    def get_success_rate(self, obj):
        if obj.total_runs > 0:
            rate = float(obj.successful_runs) / float(obj.total_runs) * 100
            color = "#28a745" if rate >= 80 else "#fd7e14" if rate >= 50 else "#dc3545"
            rate_str = f"{rate:.1f}%"
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>', color, rate_str
            )
        return "-"

    get_success_rate.short_description = "Success Rate"


# Register Celery Beat models in custom admin site
if CELERY_BEAT_AVAILABLE:
    # Unregister from default site if already registered
    from django.contrib.admin.sites import site as default_admin_site

    try:
        default_admin_site.unregister(PeriodicTask)
        default_admin_site.unregister(IntervalSchedule)
        default_admin_site.unregister(CrontabSchedule)
    except (ValueError, AttributeError, Exception):
        # Already unregistered or model doesn't exist (e.g. Celery Beat not configured)
        pass

    # Register in custom admin site
    @admin.register(PeriodicTask, site=admin_site)
    class CustomPeriodicTaskAdmin(admin.ModelAdmin):
        list_display = [
            "name",
            "get_task_display",
            "get_schedule_display",
            "enabled",
            "get_last_run",
            "total_run_count",
        ]
        list_filter = ["enabled", "task"]
        search_fields = ["name", "task", "description"]
        readonly_fields = ["date_changed", "last_run_at", "total_run_count"]
        actions = ["enable_tasks", "disable_tasks"]

        def get_task_display(self, obj):
            """Show task name with icon"""
            task_icons = {
                "scraper_manager.run_single_scraper": "🤖",
                "scraper_manager.run_all_scrapers": "🌐",
                "scraper_manager.cleanup_old_jobs": "🗑️",
                "jobs.tasks.scheduled_scraper_run": "⏰",
            }
            icon = task_icons.get(obj.task, "⚙️")
            return format_html("{} {}", icon, obj.task)

        get_task_display.short_description = "Task"

        def get_schedule_display(self, obj):
            """Show schedule in readable format"""
            if obj.crontab:
                return format_html(
                    '<span style="font-family: monospace; background: #f1f5f9; padding: 2px 6px; border-radius: 3px;">📅 {}</span>',
                    str(obj.crontab),
                )
            elif obj.interval:
                return format_html(
                    '<span style="font-family: monospace; background: #f1f5f9; padding: 2px 6px; border-radius: 3px;">⏱️ {}</span>',
                    str(obj.interval),
                )
            return "-"

        get_schedule_display.short_description = "Schedule"

        def get_last_run(self, obj):
            """Show last run time"""
            if obj.last_run_at:
                return format_html(
                    '<span style="font-size: 11px;">{}</span>',
                    obj.last_run_at.strftime("%Y-%m-%d %H:%M:%S"),
                )
            return format_html('<span style="color: #999;">Never</span>')

        get_last_run.short_description = "Last Run"

        def enable_tasks(self, request, queryset):
            updated = queryset.update(enabled=True)
            self.message_user(
                request, f"✅ Enabled {updated} task(s)", messages.SUCCESS
            )

        enable_tasks.short_description = "✅ Enable selected tasks"

        def disable_tasks(self, request, queryset):
            updated = queryset.update(enabled=False)
            self.message_user(
                request, f"⏸️ Disabled {updated} task(s)", messages.SUCCESS
            )

        disable_tasks.short_description = "⏸️ Disable selected tasks"


@admin.register(ScrapedURL, site=admin_site)
class ScrapedURLAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "get_title",
        "get_company",
        "get_source_badge",
        "scrape_count",
        "last_scraped",
        "get_active_badge",
        "get_url_link",
    ]
    list_filter = ["source", "is_active", "last_scraped"]
    search_fields = ["title", "company", "url"]
    readonly_fields = ["first_scraped", "last_scraped", "scrape_count", "url"]
    date_hierarchy = "last_scraped"
    ordering = ["-last_scraped"]
    actions = ["mark_inactive", "mark_active", "verify_url_activity"]
    list_per_page = 50

    def get_title(self, obj):
        title = obj.title[:60] + "..." if len(obj.title) > 60 else obj.title
        return format_html(
            '<div class="tooltip-wrapper"><span style="font-weight: 600; color: #1e293b;" title="{}">{}</span></div>',
            obj.title,
            title,
        )

    get_title.short_description = "Job Title"

    def get_company(self, obj):
        if obj.company:
            # Defensive import and lookup: import inside function to avoid circular import
            norm = obj.company.strip().lower()
            try:
                from jobs.models import CompanyMapping
            except Exception:
                CompanyMapping = None

            if CompanyMapping:
                try:
                    mapping = CompanyMapping.objects.get(normalized_name=norm)
                    try:
                        url = reverse(
                            "admin:jobs_companymapping_change", args=(mapping.id,)
                        )
                        return format_html(
                            '<a href="{}" style="color: #0066cc;">🏢 {}</a>',
                            url,
                            obj.company,
                        )
                    except Exception:
                        # If reverse fails for any reason, fall back to plain text
                        return obj.company
                except CompanyMapping.DoesNotExist:
                    return obj.company
                except Exception as e:
                    logger.exception(
                        "Error looking up CompanyMapping for %s: %s",
                        obj.company,
                        str(e),
                    )
                    return obj.company
            else:
                return obj.company
        return "—"

    get_company.short_description = "Company"

    def get_source_badge(self, obj):
        icons = {
            "signature": "✈️",
            "flygosh": "🛫",
            "aap": "🛩️",
            "aviationjobsearch": "🔍",
            "goose": "🦆",
        }
        icon = icons.get(obj.source, "🔧")
        return format_html(
            '<span style="background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%); color: #334155; padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 600;">{} {}</span>',
            icon,
            obj.source,
        )

    get_source_badge.short_description = "Source"

    def get_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; text-transform: uppercase;">✓ Active</span>'
            )
        return format_html(
            '<span style="background: linear-gradient(135deg, #94a3b8 0%, #64748b 100%); color: white; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; text-transform: uppercase;">⊗ Inactive</span>'
        )

    get_active_badge.short_description = "Status"

    def get_url_link(self, obj):
        """Show clickable URL link"""
        return format_html(
            '<a href="{}" target="_blank" style="background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%); color: white; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: 600; display: inline-block; transition: all 0.2s;">🔗 View</a>',
            obj.url,
        )

    get_url_link.short_description = "Link"

    def mark_inactive(self, request, queryset):
        """Mark selected URLs as inactive"""
        updated = queryset.update(is_active=False)
        self.message_user(
            request, f"Marked {updated} URL(s) as inactive", messages.SUCCESS
        )

    mark_inactive.short_description = "⊗ Mark as inactive"

    def mark_active(self, request, queryset):
        # Mark selected URLs as active
        updated = queryset.update(is_active=True)
        self.message_user(
            request, f"✅ Marked {updated} URLs as active.", messages.SUCCESS
        )

    mark_active.short_description = "✓ Mark as active"

    def verify_url_activity(self, request, queryset):
        """Verify activity status for selected URLs"""
        from .db_manager import DjangoDBManager
        import asyncio

        db = DjangoDBManager()

        if queryset.count() > 20:
            self.message_user(
                request,
                "⚠️ Please select 20 or fewer URLs for manual verification.",
                level="warning",
            )
            return

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            inactive_count = 0
            for obj in queryset:
                is_active, reason = loop.run_until_complete(
                    db.check_job_active(obj.url)
                )
                if not is_active:
                    obj.is_active = False
                    obj.save(update_fields=["is_active"])
                    inactive_count += 1

            loop.close()
            self.message_user(
                request,
                f"✅ Verification complete. {inactive_count} URL(s) marked as inactive.",
            )
        except Exception as e:
            import logging

            logger = logging.getLogger("scraper_manager")
            logger.error(f"URL Verification Error: {e}", exc_info=True)
            self.message_user(
                request, f"❌ Verification error: {str(e)}", level="error"
            )

    verify_url_activity.short_description = "🔍 Verify URL Activity"
