.PHONY: css css-watch run

ifeq ($(firstword $(MAKECMDGOALS)),run)
RUNSERVER_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
%::
	@:
endif

PYTHON ?= .venv/bin/python

# Compile Tailwind to static/css/app.css (downloads the pinned standalone CLI to
# ./bin on first run). Run once after clone, and whenever you add new utility
# classes to templates/Python/JS. The Dockerfile runs this too.
css:
	./scripts/build_css.sh

# Rebuild on every change during local development.
css-watch:
	WATCH=1 ./scripts/build_css.sh

# Compile CSS, then start the dev server (SQLite, development settings).
run: css
	$(PYTHON) manage.py migrate
	$(PYTHON) manage.py runserver $(RUNSERVER_ARGS)
