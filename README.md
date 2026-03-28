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
  workspaces/    Workspace, Membership, Invitation models + views
  api/v1/        Django Ninja REST API
templates/
  layouts/       base.html, app.html (sidebar), auth.html
  components/    sidebar, workspace switcher, messages
  account/       allauth overrides (login, signup, logout)
  workspaces/    workspace CRUD + HTMX partials
```

## Extending for a new project

1. Add nav items in `templates/components/sidebar.html`
2. Add a new Django app under `apps/`
3. Register it in `config/settings/base.py → INSTALLED_APPS`
4. Add API routers to `apps/api/v1/router.py`

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
