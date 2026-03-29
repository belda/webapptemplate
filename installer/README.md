# webapptemplate-installer

CLI installer for scaffolding new [webapptemplate](https://github.com/your-org/webapptemplate) Django projects.

## Installation

```bash
pip install webapptemplate-installer
```

## Usage

```bash
webapptemplate init
```

This runs an interactive wizard that asks a few questions and generates a complete Django project directory.

## What gets generated

```
<project_name>/
  manage.py
  config/
    __init__.py
    settings/
      __init__.py
      base.py          # imports webapptemplate.default_settings + project overrides
      development.py
      production.py
    urls.py
    wsgi.py
    asgi.py
  apps/                # empty directory for your own apps
  .env                 # generated with real SECRET_KEY, DB vars, etc.
  .env.example         # same but with placeholder values
  requirements.txt     # webapptemplate>=0.1.0
  Dockerfile           # (if selected)
  docker-compose.yml   # (if selected)
  README.md
```

## Generated settings layout

`config/settings/base.py` imports all framework defaults from the `webapptemplate` package:

```python
from webapptemplate.default_settings import *

PROJECT_NAME = "myapp"
ROOT_URLCONF = "config.urls"
# ... project-specific overrides
INSTALLED_APPS += []   # add your own apps here
```

This means you can `pip install -U webapptemplate` to pick up framework updates without touching your project config.
