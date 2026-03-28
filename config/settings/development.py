from .base import *

DEBUG = True

# Use SQLite for local development without Docker
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Override with postgres if DATABASE_URL is set
import os
if os.environ.get("DATABASE_URL") or os.environ.get("DB_HOST"):
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

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Skip email verification entirely in development so you can log in immediately
# after registration without needing to click a confirmation link.
REQUIRE_EMAIL_VERIFICATION = True
ACCOUNT_EMAIL_VERIFICATION = "none"

# Django Debug Toolbar (optional, install separately)
INTERNAL_IPS = ["127.0.0.1"]

# In development, extend the base ALLOWED_HOSTS with local dev aliases.
# Add any additional hosts (e.g. network hostnames) via the ALLOWED_HOSTS env var
# rather than hardcoding them here.
from decouple import config, Csv as _Csv
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "aisandbox.blda"] + config("EXTRA_ALLOWED_HOSTS", default="", cast=_Csv())
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:8000,http://127.0.0.1:8000",
    cast=_Csv(),
)
