# Changelog — webapptemplate-installer

## [0.1.0] — 2026-03-28

### Added
- `webapptemplate init` interactive CLI wizard
- Scaffolds complete Django project: settings, URLs, WSGI/ASGI, manage.py
- Database choices: PostgreSQL or SQLite
- Optional Redis cache/session integration
- Optional Docker + docker-compose generation
- Auto-generates SECRET_KEY using `secrets.token_urlsafe`
- Generates `.env` and `.env.example`
