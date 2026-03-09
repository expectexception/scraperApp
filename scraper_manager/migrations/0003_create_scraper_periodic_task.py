from django.db import migrations


def create_periodic_task(apps, schema_editor):
    # Use historical models via apps.get_model
    CrontabSchedule = apps.get_model('django_celery_beat', 'CrontabSchedule')
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')

    # Create or get a crontab schedule for 06:00 and 18:00 UTC daily
    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute='0',
        hour='6,18',
        day_of_week='*',
        day_of_month='*',
        month_of_year='*',
        defaults={'timezone': 'UTC'},
    )

    # Create or update the periodic task that runs the scraper manager's task
    PeriodicTask.objects.update_or_create(
        name='run_scrapers_twice_daily',
        defaults={
            'task': 'scraper_manager.tasks.run_all_scrapers',
            'crontab': schedule,
            'enabled': True,
            'kwargs': '{}',
        },
    )


def remove_periodic_task(apps, schema_editor):
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')
    CrontabSchedule = apps.get_model('django_celery_beat', 'CrontabSchedule')

    PeriodicTask.objects.filter(name='run_scrapers_twice_daily').delete()
    # Optionally remove the schedule if no other periodic tasks use it
    CrontabSchedule.objects.filter(minute='0', hour='6,18', day_of_week='*', day_of_month='*', month_of_year='*', timezone='UTC').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('scraper_manager', '0002_alter_scraperjob_status'),
        ('django_celery_beat', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_periodic_task, reverse_code=remove_periodic_task),
    ]
