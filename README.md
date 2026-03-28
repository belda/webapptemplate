# WebApp Template

A reusable Django starter kit distributed as an installable Python package. Scaffold a new
production-ready Django project in under a minute with:

- **Google OAuth + email/password auth** via `django-allauth`
- **Workspaces** — multi-tenant, with roles, invitations, and API keys
- **HTMX + Alpine.js + Tailwind CSS** — no build step required
- **Django Ninja** REST API at `/api/v1/`
- **Docker** ready — Postgres + Redis, separate dev and prod configs

---

## Creating a new project

Install the CLI (requires Python 3.11+):

```bash
pip install /path/to/webapptemplate   # local checkout; or: pip install webapptemplate (once on PyPI)
```

Scaffold a new project:

```bash
cd ~/Projects
webapptemplate init
```

The wizard prompts for project name, database (PostgreSQL or SQLite), Redis, production domain,
admin email, and whether to generate Docker files. A `SECRET_KEY` is auto-generated and written
to `.env`.

Then set up the generated project:

```bash
cd myproject
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit http://localhost:8000 — you'll be redirected to the login page.

### Run with Docker

```bash
cp .env.example .env     # set DB_PASSWORD and any other secrets

# Production-like (Postgres + Gunicorn):
docker compose up --build

# Development (hot-reload, Postgres):
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

---

## How it works

The `webapptemplate` package contains both the core Django framework and the `webapptemplate init` CLI wizard.

A scaffolded project depends only on `webapptemplate`. Its settings inherit via:

```
config/settings/production.py  (or development.py)
    └── config/settings/base.py
            └── from webapptemplate.default_settings import *
```

Framework updates are applied by bumping the `webapptemplate` version in `requirements.txt` and
running `pip install -r requirements.txt` — no need to touch project config.

---

## Extending a scaffolded project

### Add a Django app

```bash
python manage.py startapp blog apps/blog
```

Register it in `config/settings/base.py`:

```python
INSTALLED_APPS += ["apps.blog"]
```

### Add a nav item

Edit `templates/components/sidebar.html`:

```html
{% include "components/nav_item.html" with url="blog:index" label="Blog" icon="home" %}
```

Supported icons: `home`, `building`, `cog`. Add more by editing `components/nav_item.html`
with any [Font Awesome 6 Free](https://fontawesome.com/icons) icon name.

### Add an API endpoint

1. Create `apps/blog/api.py` with a `Router()`
2. Add schemas to `apps/blog/schemas.py` (or `apps/api/v1/schemas.py`)
3. Register in `config/urls.py` (or `apps/api/v1/router.py` if using the shared router):
   ```python
   from apps.blog.api import router as blog_router
   api.add_router("/blog/", blog_router)
   ```

### Override a template

Drop a file in your project's `templates/` directory with the same path as the framework
template. Project templates take precedence:

```
templates/dashboard.html          # overrides the default dashboard
templates/components/sidebar.html # overrides the sidebar
```

### Workspace-aware views

```python
from webapptemplate.apps.workspaces.decorators import workspace_member_required, workspace_admin_required

@workspace_member_required
def my_view(request):
    workspace = request.workspace   # guaranteed non-None
```

---

## Project structure (scaffolded)

```
myproject/
  manage.py
  config/
    settings/
      base.py          Shared settings — extend webapptemplate defaults here
      development.py   DEBUG=True, console email backend
      production.py    SSL/HSTS/secure cookies
    urls.py            Extends webapptemplate.urls; add project-specific routes here
    wsgi.py / asgi.py
  apps/                Your project-specific Django apps go here
  templates/           Project templates (take precedence over framework templates)
  static/              Project static files
  .env                 Secrets — never commit this
  .env.example         Committed placeholder for .env
  requirements.txt     Pinned to webapptemplate==<version>
  Dockerfile
  docker-compose.yml
  docker-compose.dev.yml
```

Framework apps (accounts, workspaces, dashboard, API) live inside the installed
`webapptemplate` package at `webapptemplate/apps/` and are imported as
`webapptemplate.apps.accounts`, etc.

---

## Configuration reference

Set these in `config/settings/base.py` (or via `.env` where noted).

| Setting | Default | Description |
|---|---|---|
| `REQUIRE_EMAIL_VERIFICATION` | `True` | Blocks email/password users until they confirm their address. Social logins and invitation acceptors are exempt. |
| `WORKSPACE_MEMBERS_CAN_INVITE` | `False` | When `True`, any workspace member can send invitations. Default: admins and owners only. |
| `USE_API` | `True` | Enables the REST API at `/api/v1/` and API key management in workspace settings. |

### Google OAuth

```bash
# .env
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
```

Then in Django admin:
1. **Sites** → change `example.com` to your domain (e.g. `localhost:8000` in dev)
2. **Social Applications** → add a Google app with your credentials and assign it to the site

Add authorized redirect URI in [Google Cloud Console](https://console.cloud.google.com/):
`https://yourdomain.com/accounts/google/login/callback/`

### Email

Development uses the `console` backend — emails print to the terminal. For production:

```bash
# .env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=you@example.com
EMAIL_HOST_PASSWORD=secret
DEFAULT_FROM_EMAIL=noreply@example.com
```

---

## Developing the template itself

To work on `webapptemplate` directly (not on a scaffolded project):

```bash
git clone <repo>
cd webapptemplate

pyenv exec python -m venv .venv
source .venv/bin/activate.fish   # or activate for bash/zsh
pip install -r requirements.txt

DJANGO_SETTINGS_MODULE=config.settings.development python manage.py runserver
```

Run checks and tests:

```bash
DJANGO_SETTINGS_MODULE=config.settings.development python manage.py check
DJANGO_SETTINGS_MODULE=config.settings.development python manage.py test
```

To test the installer locally:

```bash
pip install installer/
webapptemplate init
```

---

## Tech stack

| Layer | Library |
|---|---|
| Framework | Django 6.0.4 |
| Auth | django-allauth 65.15 |
| API | django-ninja 1.6.2 |
| Frontend | HTMX 2 + Alpine.js 3 + Tailwind CSS (CDN) |
| Static files | Whitenoise 6 |
| Database | PostgreSQL (prod) / SQLite (dev) |
| Cache / sessions | Redis + django-redis (optional) |
| Container | Docker + Compose |
| Build | Hatchling |
