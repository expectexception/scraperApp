import secrets

from django.conf import settings
from django.core import signing


TOKEN_TTL_SECONDS = 60 * 60 * 12
TOKEN_SALT = "scraper-dashboard-auth"


def dashboard_credentials() -> tuple[str, str | None]:
    return (
        getattr(settings, "DASHBOARD_USERNAME", "admin"),
        getattr(settings, "DASHBOARD_PASSWORD", None),
    )


def issue_dashboard_token(username: str) -> str:
    payload = {
        "username": username,
        "nonce": secrets.token_urlsafe(16),
    }
    return signing.dumps(payload, salt=TOKEN_SALT)


def validate_dashboard_token(token: str, *, max_age: int = TOKEN_TTL_SECONDS) -> str:
    token_data = signing.loads(token, salt=TOKEN_SALT, max_age=max_age)
    return token_data.get("username", "dashboard")
