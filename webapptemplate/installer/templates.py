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

    app_display_name = ctx.get("app_display_name", p)
    use_subscriptions = ctx.get("use_subscriptions", False)
    subscriptions_line = f"\nUSE_SUBSCRIPTIONS = True  # Enable billing / premium plans" if use_subscriptions else ""
    return f'''\
from webapptemplate.default_settings import *  # noqa: F401, F403

from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

PROJECT_NAME = "{p}"
APP_NAME = "{app_display_name}"
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
ADMINS = [("{app_display_name} Admin", config("ADMIN_EMAIL", default="{ctx["admin_email"]}"))]

SOCIALACCOUNT_PROVIDERS["google"]["APP"]["client_id"] = config("GOOGLE_CLIENT_ID", default="")
SOCIALACCOUNT_PROVIDERS["google"]["APP"]["secret"] = config("GOOGLE_CLIENT_SECRET", default="")

# Add your project-specific installed apps here:
INSTALLED_APPS += []{subscriptions_line}
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

    base_hosts = "localhost,127.0.0.1"
    extra_hosts = ctx.get("extra_allowed_hosts", [])
    allowed_hosts = base_hosts + ("," + ",".join(extra_hosts) if extra_hosts else "")
    lines = [
        f"SECRET_KEY={secret_key}",
        "DEBUG=True",
        f"ALLOWED_HOSTS={allowed_hosts}",
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
    app_name = ctx.get("app_display_name", p)
    description = ctx.get("description", "")
    desc_block = f"\n{description}\n" if description else ""
    return f'''\
# {app_name}
{desc_block}
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

In `apps/myapp/apps.py` inherit from `WebAppConfig` to auto-register nav items and URLs:

```python
from webapptemplate.app_config import WebAppConfig

class MyAppConfig(WebAppConfig):
    name = "apps.myapp"
    url_prefix = "myapp/"          # auto-includes apps/myapp/urls.py
    nav_items = [
        {{"url": "myapp:index", "label": "My App", "icon": "cog", "order": 20}},
    ]
```

Then add `"apps.myapp"` to `INSTALLED_APPS` in `config/settings/base.py` — no changes
to `config/urls.py` or templates needed.
'''


def render_claude_md(ctx):
    p = ctx["project_name"]
    app_name = ctx.get("app_display_name", p)
    description = ctx.get("description", "")
    desc_block = f"\n{description}\n" if description else ""
    domain = ctx.get("domain", f"{p}.com")
    use_postgres = ctx.get("use_postgres", True)
    use_redis = ctx.get("use_redis", True)
    use_docker = ctx.get("use_docker", True)
    use_subscriptions = ctx.get("use_subscriptions", False)

    infra_notes = []
    if use_postgres:
        infra_notes.append("- PostgreSQL database (configured via `DB_*` env vars)")
    else:
        infra_notes.append("- SQLite database (`db.sqlite3` in project root)")
    if use_redis:
        infra_notes.append("- Redis cache / sessions (configured via `REDIS_URL`)")
    if use_docker:
        infra_notes.append("- Docker Compose files for local dev and production")
    if use_subscriptions:
        infra_notes.append("- `USE_SUBSCRIPTIONS = True` — billing / premium plans enabled (wire up Stripe)")
    infra_block = "\n".join(infra_notes)

    return f'''\
# CLAUDE.md — {app_name}
{desc_block}
This project is built on **webapptemplate**, a reusable Django SaaS scaffold.

## Running the project

```bash
# Create virtualenv
python -m venv .venv
source .venv/bin/activate  # or .venv/bin/activate.fish

pip install -r requirements.txt
cp .env.example .env  # fill in SECRET_KEY etc.

# Dev server (uses config/settings/development.py by default)
python manage.py migrate
python manage.py runserver

# Run checks
python manage.py check
```

## Settings

| File | Purpose |
|------|---------|
| `config/settings/base.py` | Shared settings; imports `webapptemplate.default_settings` |
| `config/settings/development.py` | Local dev overrides |
| `config/settings/production.py` | Production / Docker |

Key project settings in `config/settings/base.py`:
- `APP_NAME = "{app_name}"` — displayed in sidebar and emails
- `ALLOWED_HOSTS` — loaded from `.env`

## Infrastructure
{infra_block}

## App layout

```
apps/
  <your apps here>
config/
  settings/
  urls.py       # extends webapptemplate.urls — no manual URL registration needed
templates/      # project-level template overrides (rarely needed)
static/
```

## Adding a new feature app

```bash
python manage.py startapp myfeature apps/myfeature
```

In `apps/myfeature/apps.py`:

```python
from webapptemplate.app_config import WebAppConfig

class MyFeatureConfig(WebAppConfig):
    name = "apps.myfeature"
    url_prefix = "myfeature/"       # auto-includes apps/myfeature/urls.py
    nav_items = [
        {{"url": "myfeature:index", "label": "My Feature", "icon": "cog", "order": 20}},
    ]
    # Optional — auto-registers a Ninja router at /api/v1/myfeature/
    # api_router_module = "apps.myfeature.api"
    # api_router_prefix = "/myfeature/"
```

Then add `"apps.myfeature"` to `INSTALLED_APPS` in `config/settings/base.py`.
No changes to `config/urls.py` or templates required.

## What webapptemplate provides

- Custom `User` model with email login (no username), avatar, `current_workspace`
- Multi-tenant **Workspace** system with `Membership` (owner/admin/member) and email **Invitations**
- Google OAuth via django-allauth
- Email verification gate (`REQUIRE_EMAIL_VERIFICATION`)
- Django Ninja REST API at `/api/v1/` with session + API key auth
- Sidebar layout with Alpine.js workspace switcher and HTMX partials
- Tailwind CSS, HTMX 2, Alpine.js 3, Font Awesome 6 (all CDN — no build step)

## Production domain

`{domain}` — update `CSRF_TRUSTED_ORIGINS` in `config/settings/production.py` if this changes.
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
