# CLAUDE.md — Project orientation

This is a **reusable Django webapp template**. The goal is to fork/copy it per project and add
app-specific functionality on top of the existing scaffolding. Keep the core structure intact when
extending.

## Running the project

```bash
# Create virtualenv (fish shell — use pyenv's Python so activate.fish is generated)
pyenv exec python -m venv .venv
source .venv/bin/activate.fish
pip install -r requirements.txt

# Dev (SQLite, no Docker needed)
DJANGO_SETTINGS_MODULE=config.settings.development python manage.py runserver

# Check for errors
DJANGO_SETTINGS_MODULE=config.settings.development python manage.py check

# Make and apply migrations
DJANGO_SETTINGS_MODULE=config.settings.development python manage.py makemigrations
DJANGO_SETTINGS_MODULE=config.settings.development python manage.py migrate

# Docker dev (Postgres + Redis, code hot-reloaded)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Docker production
docker compose up --build
```

`manage.py` defaults to `config.settings.development`. The `DJANGO_SETTINGS_MODULE` env var
overrides this; production containers set it to `config.settings.production`.

## Settings

| File                              | When used                                      |
|-----------------------------------|------------------------------------------------|
| `config/settings/base.py`         | Shared across all environments                 |
| `config/settings/development.py`  | Local dev; uses SQLite by default              |
| `config/settings/production.py`   | Docker / prod; requires Redis, real DB, SMTP   |

Env vars are loaded via `python-decouple` from a `.env` file (copy `.env.example` to start).

## App layout

```
apps/
  accounts/      Custom User model + profile settings
  workspaces/    Workspace, Membership, Invitation + all related views
  api/           Django Ninja REST API
    v1/
      router.py  NinjaAPI instance — add new routers here
      schemas.py Pydantic schemas
      accounts.py, workspaces.py  — endpoint files
```

All local apps live under `apps/`. Register new apps in `config/settings/base.py → INSTALLED_APPS`
using the full dotted path, e.g. `"apps.myapp"`.

## Key models

### `apps.accounts.models.User`
Custom user model (`AUTH_USER_MODEL`). Uses **email as the login field** (not username).
- `current_workspace` — FK to the workspace the user last switched to
- `display_name` / `initials` — computed properties used in templates
- Avatar stored as URL (pulled from Google profile on social login)

### `apps.workspaces.models`
- **`Workspace`** — name, slug (auto-generated), owner FK
- **`Membership`** — user ↔ workspace join table; roles: `owner` / `admin` / `member`
- **`Invitation`** — pending email invites with a UUID token; accepted via `/workspaces/accept-invite/<token>/`

A new personal workspace is auto-created for every user via a `post_save` signal in
`apps/workspaces/signals.py`.

## Request context

`apps/workspaces/middleware.py` adds `request.workspace` (the user's active `Workspace` or `None`).

`apps/workspaces/context_processors.py` injects into every template:
- `current_workspace` — active workspace object
- `user_workspaces` — list of all workspaces the user belongs to

Use these in templates directly; no extra queryset needed.

## URL structure

| Prefix            | File                                   | Notes                        |
|-------------------|----------------------------------------|------------------------------|
| `/`               | `apps/accounts/dashboard_urls.py`      | dashboard + home redirect    |
| `/accounts/`      | `apps/accounts/urls.py`                | profile settings             |
| `/accounts/`      | `allauth.urls`                         | login, signup, OAuth, reset  |
| `/workspaces/`    | `apps/workspaces/urls.py`              | workspace CRUD + invitations |
| `/api/v1/`        | `apps/api/v1/router.py`               | Django Ninja; docs at `/api/v1/docs` |
| `/admin/`         | Django admin                           |                              |

## Templates

```
templates/
  base.html                    HTML shell; loads Tailwind CDN, HTMX, defines blocks
  layouts/
    app.html                   Authenticated layout: sidebar + topbar + main content
    auth.html                  Centered card layout for login/signup
  components/
    sidebar.html               Dark sidebar; include nav items here for new features
    nav_item.html              Single sidebar link (icon + label + active state)
    workspace_switcher.html    Alpine.js dropdown in sidebar header
    messages.html              Django flash messages
  account/                     Allauth overrides (login, signup, logout)
  accounts/                    Profile settings page
  workspaces/
    settings.html              Workspace settings: rename, members, invites
    partials/                  HTMX swap targets (members_list, pending_invitations)
  dashboard.html               Main dashboard (extend this per project)
```

**To add a new page:** extend `layouts/app.html` and fill `{% block content %}`.

**To add HTMX partials:** create under `templates/<app>/partials/`, return them from views when
`request.headers.get("HX-Request")` is truthy.

## Frontend libraries (all via CDN, no build step)

- **Tailwind CSS** — utility classes; configured inline in `base.html`
- **HTMX 2** — `hx-post`, `hx-get`, `hx-target`, `hx-swap` on forms/buttons
- **Alpine.js 3** — lightweight reactivity for dropdowns etc. (loaded in `workspace_switcher.html`)
- **Font Awesome 6 Free** — icon library loaded in `base.html`; use `<i class="fa-solid fa-<name>">` throughout

## Auth (django-allauth)

- Login methods: email+password **and** Google OAuth
- `ACCOUNT_LOGIN_METHODS = {"email"}` — no username login
- `ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]`
- Custom adapters in `apps/accounts/adapters.py`:
  - `AccountAdapter` — username falls back to email prefix; redirects to pending invite after login/signup
  - `SocialAccountAdapter` — pulls avatar + name from Google profile data
- Google app credentials come from `.env` (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`)
- After registering Google credentials, set the Site in Django admin to match the domain

## Email verification

`REQUIRE_EMAIL_VERIFICATION = True` (in `base.py`) blocks unverified email/password users
from accessing the app. Three categories of users are always treated as verified:

1. **Social logins** (Google etc.) — allauth marks the email verified automatically.
2. **Invitation acceptors** — clicking an invite link proves ownership of the email;
   `accept_invitation` calls `EmailAddress.update_or_create(verified=True)` on accept.
3. Disable entirely with `REQUIRE_EMAIL_VERIFICATION = False`.

The verification-pending splash page (`/accounts/email-verification-pending/`) sends the
confirmation email **automatically on first visit** (tracked in the session), so users
don't need to click "Resend" manually.

## Invitation flow

When an unauthenticated user clicks an invite link:
1. The `accept_invitation` view stores the token in `request.session["pending_invite_token"]`
   and redirects to `/accounts/signup/?next=/workspaces/accept-invite/<token>/`.
2. After sign-up (or login), allauth follows the `?next=` URL back to the invite view.
   If the `?next=` param is lost (e.g. user navigates to signup manually), `AccountAdapter.
   get_login_redirect_url` reads the session token and redirects there instead.
3. On accept the user is added as a `member` of the workspace, their `current_workspace`
   is set, and their email is marked verified. They land directly on the dashboard inside
   the invited workspace.

**Inviting new members:** by default only admins/owners can send invites. Set
`WORKSPACE_MEMBERS_CAN_INVITE = True` in settings to let any workspace member invite.

## Adding a new API endpoint

1. Create `apps/api/v1/myfeature.py` with a `Router()`
2. Add schemas to `apps/api/v1/schemas.py`
3. Register in `apps/api/v1/router.py`: `api.add_router("/myfeature/", myfeature_router)`

All API endpoints are session-authenticated by default (`auth=django_auth` on the `NinjaAPI`
instance). Override per-endpoint with `@router.get(..., auth=None)` for public endpoints.

## Adding a new nav item

Edit `templates/components/sidebar.html` and add:

```html
{% include "components/nav_item.html" with url="my_view_name" label="My Feature" icon="home" %}
```

Supported icon values: `home` → `fa-house`, `building` → `fa-building`, `cog` → `fa-gear`.
To add more, add an `{% elif icon == "myicon" %}` branch in `components/nav_item.html` using any
[Font Awesome 6 Free](https://fontawesome.com/icons?d=gallery&o=r&m=free) icon name.

## Workspace-aware views

Use the decorators in `apps/workspaces/decorators.py`:

```python
from apps.workspaces.decorators import workspace_member_required, workspace_admin_required

@workspace_member_required
def my_view(request):
    workspace = request.workspace  # guaranteed non-None
```

## Migrations note

The `accounts` app has a two-step initial migration (`0001`, `0002`) because `current_workspace`
is a circular FK to `workspaces`. This is normal — don't collapse them.

---

## What's already built

Use this as a quick reference before adding something — it may already exist.

### Auth & accounts
- [x] Custom `User` model — email login, `display_name`, `initials`, `avatar` (URL), `current_workspace` FK
- [x] Email + password login via django-allauth
- [x] Google OAuth login — pulls avatar + display name from profile
- [x] Profile settings page (`/accounts/profile/`)
- [x] `AccountAdapter` — username falls back to email prefix; redirects to pending invite after auth
- [x] `SocialAccountAdapter` — syncs avatar + name from Google

### Workspaces
- [x] `Workspace` model — name, auto-slug, owner FK, `created_at`
- [x] `Membership` model — user ↔ workspace join; roles: `owner` / `admin` / `member`
- [x] `Invitation` model — UUID token, `email`, `invited_by`, `accepted_at`, expiry
- [x] Auto-create personal workspace on user signup (post_save signal)
- [x] Workspace create / switch / list views
- [x] Workspace settings — rename (admin only), members list, invite by email, cancel invite, remove member
- [x] Email invitation with accept link (`/workspaces/accept-invite/<token>/`)
- [x] Invitation flow for new users — redirects to signup, preserves token, auto-joins workspace after registration
- [x] Accepting invitation marks email as verified — no separate confirmation step needed
- [x] `WORKSPACE_MEMBERS_CAN_INVITE` setting — controls whether members can invite (default: admins only)
- [x] HTMX-powered partials: `members_list`, `pending_invitations`, `create_form`, `api_keys_list`
- [x] `workspace_member_required` / `workspace_admin_required` decorators
- [x] `CurrentWorkspaceMiddleware` — `request.workspace`
- [x] `workspace_context` context processor — `current_workspace`, `user_workspaces` in all templates
- [x] `APIKey` model — workspace-scoped; stores prefix + SHA-256 hash; raw key shown once on creation
- [x] API key CRUD in workspace settings (admin-only); HTMX-powered list with inline rename

### API
- [x] Django Ninja v1 at `/api/v1/` — session auth **and** Bearer token auth (API key)
- [x] `/api/v1/accounts/` endpoints
- [x] `/api/v1/workspaces/` endpoints
- [x] Interactive docs at `/api/v1/docs`
- [x] `USE_API` setting — gates `/api/v1/` URLs and API keys section in workspace settings

### Frontend
- [x] Tailwind CSS (CDN — no build step)
- [x] HTMX 2 (CDN)
- [x] Alpine.js 3 (CDN — used in workspace switcher dropdown)
- [x] Font Awesome 6 Free (CDN — icons throughout sidebar and nav)
- [x] `layouts/app.html` — sidebar + topbar authenticated shell
- [x] `layouts/auth.html` — centered card for login/signup
- [x] Sidebar with nav items, workspace switcher
- [x] Django flash messages component

### Infrastructure
- [x] `python-decouple` env var loading from `.env`
- [x] SQLite for local dev, PostgreSQL for Docker/prod
- [x] Whitenoise static file serving
- [x] Redis in Docker (`django-redis` installed, cache backend wired in prod)
- [x] Docker Compose: `docker-compose.yml` (prod) + `docker-compose.dev.yml` (dev hot-reload)
- [x] Gunicorn WSGI server in production container
- [x] `REQUIRE_EMAIL_VERIFICATION` setting — gates app access until email confirmed; bypassed for social login and invitation acceptors
- [x] Verification-pending page auto-sends confirmation email on first visit (no manual "Resend" needed)

---

## TODO — things that could be added

These are natural extensions to this template. Check the list above before starting; something
may already be in place.

### High value / common needs
- [x] **Tests** — Django test suite covering accounts, workspaces views, API endpoints, and API key management/auth
- [ ] **Email verification in dev** — configure a real SMTP backend (currently uses `console` backend; emails print to terminal)
- [ ] **Celery + Redis** — Redis is in Docker already; wire up `celery` for async tasks (emails, etc.)
- [x] **API token auth** — workspace-scoped `APIKey` model; `APIKeyAuth` Bearer class in `apps/api/v1/auth.py`
- [ ] **Role management UI** — promote/demote members between `admin` ↔ `member` in workspace settings
- [ ] **Leave workspace** — member-initiated self-removal view
- [ ] **Delete workspace** — owner-only; reassign or cascade-delete data

### Auth & accounts
- [ ] **Additional OAuth providers** — GitHub, Microsoft, etc. (allauth has built-in support)
- [ ] **Account deletion / GDPR** — user-initiated full account + data removal
- [ ] **2FA** — django-allauth supports TOTP; enable `allauth.mfa`

### Storage & media
- [ ] **S3 / object storage** — `Pillow` is installed; wire up `django-storages` for `MEDIA_ROOT` in prod
- [ ] **Avatar upload** — currently avatar is a URL from Google; add local upload fallback

### Features
- [ ] **Audit log** — track who did what in a workspace (model + middleware)
- [ ] **Notifications** — in-app or email digest
- [ ] **Billing / subscriptions** — Stripe integration (plan limits per workspace)
- [ ] **Feature flags** — per-workspace or per-user flag system
- [ ] **Pagination** — member lists and any future list views
- [ ] **Webhooks** — outbound event delivery for workspace actions

### Frontend / DX
- [ ] **More sidebar icons** — only `home`, `building`, `cog` exist; add FA icon branches to `nav_item.html`
- [ ] **Dark mode** — Tailwind `dark:` classes + Alpine toggle
- [ ] **Toast notifications** — HTMX `HX-Trigger` already used; wire up a toast component
- [ ] **Local Tailwind build** — replace CDN with a proper `tailwind.config.js` + PostCSS pipeline for prod

### Ops
- [ ] **CI/CD pipeline** — GitHub Actions: lint, test, build Docker image
- [ ] **Sentry** — error tracking (`sentry-sdk[django]`)
- [ ] **Health-check endpoint** — `/health/` returning 200 for load-balancer probes
- [ ] **`django-extensions`** — `shell_plus`, `runserver_plus` for development ergonomics
- [ ] **Logging config** — structured JSON logging for production containers
