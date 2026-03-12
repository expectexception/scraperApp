from django.http import JsonResponse
from django.urls import include, path

urlpatterns = [
    path("health", lambda request: JsonResponse({"ok": True, "service": "scraper"})),
    path("api/scrapers/", include("scraper_manager.urls")),
]

