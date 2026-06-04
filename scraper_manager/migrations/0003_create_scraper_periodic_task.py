from django.db import migrations


def create_periodic_task(apps, schema_editor):
    try:
        CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
        PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute="0",
            hour="6,18",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
            defaults={"timezone": "UTC"},
        )

        PeriodicTask.objects.update_or_create(
            name="run_scrapers_twice_daily",
            defaults={
                "task": "scraper_manager.tasks.run_all_scrapers",
                "crontab": schedule,
                "enabled": True,
                "kwargs": "{}",
            },
        )
    except Exception:
        # Older Mongo/ObjectId-backed deployments can already have celery beat
        # collections in place but not support this historical FK write path.
        # Skip the bootstrap task; current runtime scheduling is managed by code.
        return


def remove_periodic_task(apps, schema_editor):
    try:
        PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
        CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")

        PeriodicTask.objects.filter(name="run_scrapers_twice_daily").delete()
        CrontabSchedule.objects.filter(
            minute="0",
            hour="6,18",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
            timezone="UTC",
        ).delete()
    except Exception:
        return


class Migration(migrations.Migration):
    dependencies = [
        ("scraper_manager", "0002_alter_scraperjob_status"),
        ("django_celery_beat", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_periodic_task, reverse_code=remove_periodic_task),
    ]
