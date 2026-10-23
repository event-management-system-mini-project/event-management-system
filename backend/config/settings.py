import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")
DEBUG = os.getenv("EMS_DEBUG", "0") == "1"
SECRET_KEY = os.getenv("EMS_SECRET_KEY", "")
if len(SECRET_KEY) < 32:
    raise ImproperlyConfigured(
        "Set a random EMS_SECRET_KEY of at least 32 characters; "
        "python scripts/bootstrap.py creates a local .env."
    )

ALLOWED_HOSTS = [
    value.strip() for value in
    os.getenv("EMS_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if value.strip()
]
CSRF_TRUSTED_ORIGINS = [
    value.strip() for value in
    os.getenv("EMS_CSRF_TRUSTED_ORIGINS", "").split(",") if value.strip()
]
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "events.apps.EventsConfig",
    "rest_framework",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
AUTH_USER_MODEL = "events.Organizer"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
TIME_ZONE = "Asia/Kolkata"
USE_TZ = True
LANGUAGE_CODE = "en-us"
APPEND_SLASH = False

database_name = os.getenv("EMS_DB_PATH", "data/events.sqlite3")
database_path = Path(database_name)
if not database_path.is_absolute():
    database_path = ROOT_DIR / database_path
database_path.parent.mkdir(parents=True, exist_ok=True)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(database_path),
        "OPTIONS": {"timeout": 10},
        # Repository acknowledgements must not occur inside an outer request transaction.
        "ATOMIC_REQUESTS": False,
    }
}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
CSRF_FAILURE_VIEW = "events.http.csrf_failure"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = not DEBUG
SESSION_ENGINE = "django.contrib.sessions.backends.db"
