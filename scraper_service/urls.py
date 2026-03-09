from django.http import JsonResponse
from django.urls import path

urlpatterns = [
    path("health", lambda request: JsonResponse({"ok": True, "service": "scraper"})),
]
