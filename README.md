# WebApp Template

A reusable Django starter with:
- **Google OAuth + email/password auth** via `django-allauth`
- **Workspaces** — create, switch, invite teammates
- **HTMX** frontend with Tailwind CSS + Alpine.js
- **Django Ninja** REST API (`/api/v1/`)
- **Docker** ready (Postgres + Redis)

## Quick start (local, SQLite)

```bash
# 1. Create virtualenv and install deps
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Copy env and configure
cp .env.example .env        # edit GOOGLE_CLIENT_ID / SECRET at minimum

# 3. Run migrations and create superuser
python manage.py migrate
python manage.py createsuperuser

# 4. Start dev server
python manage.py runserver
```

Visit http://localhost:8000 — you'll be redirected to the login page.

## Docker (recommended for production-like setup)

```bash
cp .env.example .env        # fill in secrets

# Dev (code hot-reloaded, SQLite skipped, uses Postgres):
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Production:
docker compose up --build
```

## Google OAuth setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials
2. Create an **OAuth 2.0 Client ID** (Web application)
3. Add Authorized redirect URI: `http://localhost:8000/accounts/google/login/callback/`
4. Copy Client ID and Secret into `.env`
5. In Django admin → Sites → change `example.com` to `localhost:8000`
6. In Django admin → Social Applications → add Google app with your credentials

## Project structure

```
config/          Django settings (base / development / production)
apps/
  accounts/      Custom User model, profile settings, allauth adapters
    api.py       /api/v1/accounts/ endpoints
    schemas.py   Pydantic schemas for accounts
    templates/   Auth + profile templates (account/, accounts/)
  workspaces/    Workspace, Membership, Invitation, APIKey models + views
    api.py       /api/v1/workspaces/ endpoints
    api_auth.py  APIKeyAuth Bearer class
    schemas.py   Pydantic schemas for workspaces
    templates/   Workspace templates + HTMX partials
  dashboard/     Home redirect + dashboard view
    templates/   dashboard.html (extend this per project)
  api/v1/        Central API router — imports from app packages
templates/
  base.html      HTML shell
  landing.html   Public landing page
  layouts/       app.html (sidebar), auth.html
  components/    sidebar, workspace switcher, messages
```

## Extending for a new project

1. Add nav items in `templates/components/sidebar.html`
2. Add a new Django app under `apps/` with its own `api.py`, `schemas.py`, and `templates/`
3. Register it in `config/settings/base.py → INSTALLED_APPS`
4. Add API routers to `apps/api/v1/router.py`

## Configuration reference

All custom settings live in `config/settings/base.py` and can be overridden per environment or via `.env`.

| Setting | Default | Description |
|---------|---------|-------------|
| `REQUIRE_EMAIL_VERIFICATION` | `True` | When `True`, email/password users must confirm their address before accessing the app. Social logins (Google) and invitation acceptors bypass this. Set to `False` to disable. |
| `WORKSPACE_MEMBERS_CAN_INVITE` | `True` | When `True`, any workspace member can send invitations. When `False`, only admins and owners can. |
| `USE_API` | `True` | When `True`, the REST API at `/api/v1/` is reachable and API key management appears in workspace settings. Set to `False` to disable the API entirely. |

### Google OAuth

Set these in `.env` (or environment):

```
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
```

Then in Django admin: update the **Site** to match your domain, and add a **Social Application** for Google.

### Email

By default `EMAIL_BACKEND` is `console` (prints to terminal). For production, configure SMTP via `.env`:

```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=you@example.com
EMAIL_HOST_PASSWORD=secret
DEFAULT_FROM_EMAIL=noreply@example.com
```

## Tech stack

| Layer      | Library                  |
|------------|--------------------------|
| Framework  | Django 5.0               |
| Auth       | django-allauth 0.62      |
| API        | django-ninja 1.1         |
| Frontend   | HTMX 2 + Alpine.js 3     |
| CSS        | Tailwind CSS (CDN)       |
| Static     | Whitenoise               |
| Database   | PostgreSQL / SQLite (dev)|
| Cache      | Redis (optional)         |
| Container  | Docker + Compose         |
