"""
Template rendering functions for scaffold.py.
Each function returns a string with the rendered file content.
"""


def render_manage_py(ctx):
    p = ctx["project_name"]
    return f'''#!/usr/bin/env python
"""Django management script for {p}."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
'''


def render_settings_base(ctx):
    p = ctx["project_name"]
    use_postgres = ctx["use_postgres"]
    use_redis = ctx["use_redis"]

    if use_postgres:
        db_block = """\
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="{p}"),
        "USER": config("DB_USER", default="postgres"),
        "PASSWORD": config("DB_PASSWORD", default="postgres"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}""".replace("{p}", p)
    else:
        db_block = """\
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}"""

    if use_redis:
        cache_block = """\
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_URL", default="redis://127.0.0.1:6379/1"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
"""
    else:
        cache_block = """\
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.db"
"""

    return f'''\
from webapptemplate.default_settings import *  # noqa: F401, F403

from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

PROJECT_NAME = "{p}"
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Project templates take precedence over package templates
TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"] + list(TEMPLATES[0]["DIRS"])

# Project static files alongside package static files
STATICFILES_DIRS = [BASE_DIR / "static"] + [
    d for d in STATICFILES_DIRS if d != BASE_DIR / "static"
]

SECRET_KEY = config("SECRET_KEY")

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

{db_block}

STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@{ctx["domain"]}")

{cache_block}
ADMINS = [("{p} Admin", config("ADMIN_EMAIL", default="{ctx["admin_email"]}"))]

SOCIALACCOUNT_PROVIDERS["google"]["APP"]["client_id"] = config("GOOGLE_CLIENT_ID", default="")
SOCIALACCOUNT_PROVIDERS["google"]["APP"]["secret"] = config("GOOGLE_CLIENT_SECRET", default="")

# Add your project-specific installed apps here:
INSTALLED_APPS += []
'''


def render_settings_dev(ctx):
    p = ctx["project_name"]
    return f'''\
from config.settings.base import *  # noqa: F401, F403

DEBUG = True

# Show emails in terminal during development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
'''


def render_settings_prod(ctx):
    p = ctx["project_name"]
    domain = ctx["domain"]
    return f'''\
from config.settings.base import *  # noqa: F401, F403
from decouple import config

DEBUG = False

CSRF_TRUSTED_ORIGINS = [
    "https://{domain}",
    "https://www.{domain}",
]

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Use a real email backend in production — configure via .env
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# EMAIL_HOST = ...
'''


def render_urls(ctx):
    return '''\
from webapptemplate.urls import urlpatterns as wt_urlpatterns
from django.urls import path

urlpatterns = wt_urlpatterns + [
    # Add your project-specific URLs here
]
'''


def render_wsgi(ctx):
    p = ctx["project_name"]
    return f'''\
"""WSGI config for {p}."""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
application = get_wsgi_application()
'''


def render_asgi(ctx):
    p = ctx["project_name"]
    return f'''\
"""ASGI config for {p}."""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
application = get_asgi_application()
'''


def render_env(ctx, example=False):
    p = ctx["project_name"]
    use_postgres = ctx["use_postgres"]
    use_redis = ctx["use_redis"]
    secret_key = "your-secret-key-here" if example else ctx["secret_key"]
    db_pass = "your-db-password" if example else "postgres"
    redis_url = "redis://127.0.0.1:6379/1"

    lines = [
        f"SECRET_KEY={secret_key}",
        "DEBUG=True",
        f"ALLOWED_HOSTS=localhost,127.0.0.1",
        "",
        "# Email",
        f"DEFAULT_FROM_EMAIL=noreply@{ctx['domain']}",
        "# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend",
        "",
        "# Google OAuth (optional)",
        "GOOGLE_CLIENT_ID=",
        "GOOGLE_CLIENT_SECRET=",
        "",
        f"ADMIN_EMAIL={ctx['admin_email']}",
    ]

    if use_postgres:
        lines += [
            "",
            "# PostgreSQL",
            f"DB_NAME={p}",
            "DB_USER=postgres",
            f"DB_PASSWORD={db_pass}",
            "DB_HOST=localhost",
            "DB_PORT=5432",
        ]

    if use_redis:
        lines += [
            "",
            "# Redis",
            f"REDIS_URL={redis_url}",
        ]

    return "\n".join(lines) + "\n"


def render_gitignore(ctx):
    return '''\
# Python
__pycache__/
*.py[cod]
*.egg-info/
.eggs/
dist/
build/
*.so

# Django
*.sqlite3
staticfiles/
media/
local_settings.py

# Environment
.env
.venv
venv/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Docker
*.log
'''


def render_readme(ctx):
    p = ctx["project_name"]
    return f'''\
# {p}

Built with [webapptemplate](https://github.com/your-org/webapptemplate).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv/bin/activate.fish
pip install -r requirements.txt
cp .env.example .env       # edit .env with your values
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Settings

| File | When used |
|------|-----------|
| `config/settings/base.py` | Shared across all environments |
| `config/settings/development.py` | Local dev |
| `config/settings/production.py` | Docker / production |

## Adding a new app

```bash
python manage.py startapp myapp apps/myapp
```

Then add `"apps.myapp"` to `INSTALLED_APPS` in `config/settings/base.py`.
'''


def render_dockerignore(ctx):
    return '''\
.env
.venv
venv/
__pycache__/
*.py[cod]
*.egg-info/
.git/
.gitignore
db.sqlite3
staticfiles/
media/
*.log
'''


def render_dockerfile(ctx):
    return '''\
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \\
    libpq-dev gcc \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
'''


def render_docker_compose(ctx):
    p = ctx["project_name"]
    use_redis = ctx["use_redis"]

    redis_service = ""
    redis_depends = ""
    redis_env = ""
    if use_redis:
        redis_service = """\
  redis:
    image: redis:7-alpine
    restart: unless-stopped

"""
        redis_depends = "\n      redis:\n        condition: service_started"
        redis_env = "\n      - REDIS_URL=redis://redis:6379/1"

    return f'''\
services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: {p}
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${{DB_PASSWORD:-postgres}}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

{redis_service}  web:
    build: .
    restart: unless-stopped
    env_file: .env
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.production
      - DB_HOST=db
      - DB_NAME={p}{redis_env}
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy{redis_depends}
    command: >
      sh -c "python manage.py migrate &&
             gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2"

volumes:
  postgres_data:
'''


def render_docker_compose_dev(ctx):
    p = ctx["project_name"]
    return f'''\
# Extend docker-compose.yml for local development with hot reload.
# Usage: docker compose -f docker-compose.yml -f docker-compose.dev.yml up

services:
  web:
    volumes:
      - .:/app
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.development
      - DEBUG=True
    command: python manage.py runserver 0.0.0.0:8000
    ports:
      - "8000:8000"
'''
