from django.apps import AppConfig


class ScraperManagerConfig(AppConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"
    name = "scraper_manager"
