# Changelog — webapptemplate

## [Unreleased]

Fixes and subsystems proven in a downstream project (AndelSound) and folded back
into the template.

### Fixed
- **The active workspace is now session-scoped.** It was read from
  `User.current_workspace` on every request, so switching workspace in one
  browser silently moved every other logged-in session for that account
  (including an admin's impersonation session). It now lives in the session;
  `User.current_workspace` is only the hint that seeds a fresh login. Route all
  switches through `workspaces.middleware.set_current_workspace`.
- **API keys no longer escalate across workspaces.** `APIKeyAuth` never bound a
  principal, so `request.user` was anonymous under Bearer auth and every
  workspace-scoped endpoint misbehaved; and nothing pinned a key to the
  workspace it was minted for, so a leaked key reached every other workspace its
  creator belonged to. Keys now authenticate as their creator, are rejected when
  that account is inactive or gone, and endpoints enforce the pin via
  `require_key_workspace()`.
- **htmx no longer re-opens hidden Alpine elements.** htmx's settle phase
  re-applied server-rendered `class`/`style` over any swapped-in element with a
  stable id, wiping the inline `display: none` that `x-show` had just set —
  hidden panels popped open after every swap. `attributesToSettle` is now empty.
- **`x-cloak` moved to a plain `<style>` block.** Registered inside a
  Tailwind-processed block, the rule only existed after the compile pass, and
  browsers that let Alpine run first (Safari) flashed every cloaked element.
- **The on-screen keyboard no longer hides the bottom of long forms.** The
  viewport meta now sets `interactive-widget=resizes-content`.
- **`{% static %}` works on a fresh clone.** Development settings kept the
  production manifest storage, so any template referencing a static asset raised
  "Missing staticfiles manifest entry" until `collectstatic` had run.

### Added
- **Tailwind is precompiled** by the standalone CLI (`make css`,
  `tailwind.config.js`, `scripts/build_css.sh`) instead of loading
  `cdn.tailwindcss.com`. The Play CDN is not production software and drops
  comma-containing arbitrary utilities on some WebKit builds. Also adds a
  `Makefile` (`make run`, `make css-watch`).
- **`webapptemplate.apps.deploy`** — post-deploy steps: run-once management
  commands, recorded and retried, with a `post_deploy` runner. See the README.
- **`webapptemplate.apps.feedback`** — in-app bug/wish reports capturing page
  URL, user agent and viewport, with an optional screenshot and an operator
  reply thread that emails the reporter.
- **`{% asset %}`** template tag — static URL with an mtime cache-buster in
  DEBUG, a plain hashed URL in production.
- **`workspaces.http.htmx_redirect()`** — 204 + `HX-Redirect`, replacing four
  hand-rolled copies.
- **`?next=` survives email confirmation.** The account adapter stashes a
  validated, same-host `next` at signup and replays it after the confirmation
  hop, where the query string is gone.

## [0.1.0] — 2026-03-28

### Added
- Initial PyPI-distributable package structure
- `webapptemplate.default_settings` — reusable Django settings base
- `webapptemplate.urls` — exportable base URL patterns
- `webapptemplate/` Python package with contrib sub-package
- `pyproject.toml` using hatchling build backend
- Packaging includes `apps/`, `templates/`, and `static/`
