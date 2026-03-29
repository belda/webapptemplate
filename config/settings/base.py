from webapptemplate.default_settings import *  # noqa: F401, F403

from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Project templates take precedence over package templates
TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"] + list(TEMPLATES[0]["DIRS"])

# Project static files alongside package static files
STATICFILES_DIRS = [BASE_DIR / "static"] + [
    d for d in STATICFILES_DIRS if d != BASE_DIR / "static"
]

SECRET_KEY = config("SECRET_KEY", default="django-insecure-change-me")

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="webapptemplate"),
        "USER": config("DB_USER", default="postgres"),
        "PASSWORD": config("DB_PASSWORD", default="postgres"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Email
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@webapptemplate.local")

# Cache / Sessions
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# Google OAuth credentials
SOCIALACCOUNT_PROVIDERS["google"]["APP"]["client_id"] = config("GOOGLE_CLIENT_ID", default="")
SOCIALACCOUNT_PROVIDERS["google"]["APP"]["secret"] = config("GOOGLE_CLIENT_SECRET", default="")
