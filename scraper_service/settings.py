import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# If scraper .env does not include MongoDB credentials, try backend .env so
# both services can share the same database without duplicated config.
BACKEND_ENV_PATH = BASE_DIR.parent / "aeroScrap_backend" / "backendMain" / ".env"
current_mongo_uri = (os.environ.get("MONGODB_URI") or "").strip()
if BACKEND_ENV_PATH.exists() and (not current_mongo_uri or "<db_password>" in current_mongo_uri):
    backend_env = dotenv_values(BACKEND_ENV_PATH)
    backend_mongo_uri = (backend_env.get("MONGODB_URI") or "").strip()
    backend_mongo_name = (backend_env.get("MONGODB_NAME") or backend_env.get("DB_NAME") or "").strip()

    if backend_mongo_uri:
        os.environ["MONGODB_URI"] = backend_mongo_uri
    if backend_mongo_name and not os.environ.get("MONGODB_NAME"):
        os.environ["MONGODB_NAME"] = backend_mongo_name

SECRET_KEY = os.environ.get("SECRET_KEY", "scraper-service-dev-key")
DEBUG = os.environ.get("DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]

DASHBOARD_USERNAME = os.environ.get("DASHBOARD_USERNAME", "admin")
DASHBOARD_PASSWORD = (
    os.environ.get("DASHBOARD_PASSWORD")
    or os.environ.get("ADMIN_PASSWORD")
    or os.environ.get("AEROOPS_PASSWORD")
    or "takla"
)
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "corsheaders",
    "rest_framework",
    "django_celery_beat",
    "jobs",
    "scraper_manager",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

CORS_ALLOWED_ORIGINS = [
    os.environ.get("FRONTEND_URL", "http://localhost:8501"),
    "http://localhost:5173",
]
CORS_ALLOW_CREDENTIALS = True

ROOT_URLCONF = "scraper_service.urls"
TEMPLATES = []
WSGI_APPLICATION = "scraper_service.wsgi.application"

# Database Configuration (MongoDB only)
DATABASE_ENGINE = os.environ.get("DATABASE_ENGINE", "mongodb").strip().lower()
if DATABASE_ENGINE not in {"mongodb", "mongo", "django_mongodb_backend"}:
    raise ValueError("Only MongoDB is supported. Set DATABASE_ENGINE=mongodb.")

mongodb_uri = os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI") or os.environ.get("DB_HOST")
mongodb_name = os.environ.get("MONGODB_NAME") or os.environ.get("DB_NAME") or "aeroops_db"

if not mongodb_uri:
    raise ValueError("MONGODB_URI is required when DATABASE_ENGINE=mongodb.")

DATABASES = {
    "default": {
        "ENGINE": "django_mongodb_backend",
        "HOST": mongodb_uri,
        "NAME": mongodb_name,
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django_mongodb_backend.fields.ObjectIdAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
}
