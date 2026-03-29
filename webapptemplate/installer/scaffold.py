"""
Project scaffolding logic for `webapptemplate init`.
"""
import re
import sys
import secrets
from pathlib import Path

import webapptemplate
from webapptemplate.installer import templates as tmpl


def prompt(question, default=None, choices=None):
    """Simple prompt with optional default and choices."""
    if choices:
        choice_str = "/".join(
            c.upper() if c == default else c for c in choices
        )
        question = f"{question} [{choice_str}]"
    elif default is not None:
        question = f"{question} [{default}]"

    while True:
        answer = input(f"{question}: ").strip()
        if not answer and default is not None:
            return default
        if not answer:
            print("  This field is required.")
            continue
        if choices and answer.lower() not in [c.lower() for c in choices]:
            print(f"  Please choose one of: {', '.join(choices)}")
            continue
        return answer


def prompt_optional(question):
    """Prompt that accepts an empty answer (returns empty string)."""
    return input(f"{question}: ").strip()


def prompt_bool(question, default=True):
    default_str = "y" if default else "n"
    answer = prompt(question, default=default_str, choices=["y", "n"])
    return answer.lower() == "y"


def slugify(name):
    return re.sub(r"[^a-z0-9_]", "_", name.lower()).strip("_")


def generate_secret_key():
    return secrets.token_urlsafe(50)


def run_wizard():
    print()
    print("  webapptemplate project scaffolder")
    print("  ──────────────────────────────────")
    print()

    # 1. Project name (Python identifier)
    project_name = prompt("Project name (Python identifier, e.g. myapp)")
    project_name = slugify(project_name)
    if not project_name:
        print("Invalid project name.")
        sys.exit(1)

    # 2. App display name (shown in sidebar, emails, docs)
    default_display = project_name.replace("_", " ").title()
    app_display_name = prompt(
        "App display name (shown in sidebar and emails)",
        default=default_display,
    )

    # 3. Short project description (1–2 sentences for README / CLAUDE.md)
    print("  Project description (1–2 sentences, press Enter to skip):")
    description = prompt_optional("  Description")

    # 4. Database
    db_choice = prompt(
        "Database backend",
        default="postgresql",
        choices=["postgresql", "sqlite"],
    )
    use_postgres = db_choice == "postgresql"

    # 5. Redis
    use_redis = prompt_bool("Include Redis (cache / sessions)?", default=True)

    # 6. Domain
    domain = prompt("Production domain (e.g. myapp.com)", default=f"{project_name}.com")

    # 7. Admin email
    admin_email = prompt("Admin email address", default=f"admin@{domain}")

    # 8. Additional ALLOWED_HOSTS for development (beyond localhost/127.0.0.1)
    print("  Extra development ALLOWED_HOSTS (comma-separated, e.g. myapp.local)")
    print("  Leave blank to use only localhost and 127.0.0.1")
    extra_hosts_raw = prompt_optional("  Extra hosts")
    extra_allowed_hosts = [h.strip() for h in extra_hosts_raw.split(",") if h.strip()]

    # 9. Docker
    use_docker = prompt_bool("Generate Dockerfile + docker-compose.yml?", default=True)

    # 10. Secret key (auto-generated, shown to user)
    secret_key = generate_secret_key()
    print(f"\n  Auto-generated SECRET_KEY: {secret_key}")
    print("  (saved to .env — keep it secret)\n")

    # Collect config
    ctx = {
        "project_name": project_name,
        "app_display_name": app_display_name,
        "description": description,
        "use_postgres": use_postgres,
        "use_redis": use_redis,
        "domain": domain,
        "admin_email": admin_email,
        "extra_allowed_hosts": extra_allowed_hosts,
        "use_docker": use_docker,
        "secret_key": secret_key,
    }

    # Destination directory
    dest = Path.cwd() / project_name
    if dest.exists():
        overwrite = prompt_bool(f"Directory '{project_name}/' already exists. Continue?", default=False)
        if not overwrite:
            print("Aborted.")
            sys.exit(1)

    print(f"\n  Scaffolding project in ./{project_name}/\n")
    scaffold_project(dest, ctx)
    print(f"  Done! Next steps:\n")
    print(f"    cd {project_name}")
    print(f"    pip install -r requirements.txt")
    print(f"    python manage.py migrate")
    print(f"    python manage.py createsuperuser")
    print(f"    python manage.py runserver")
    print()


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    print(f"  + {path}")


def scaffold_project(dest: Path, ctx: dict):
    use_docker = ctx["use_docker"]

    # manage.py
    write_file(dest / "manage.py", tmpl.render_manage_py(ctx))

    # config/
    write_file(dest / "config" / "__init__.py", "")
    write_file(dest / "config" / "settings" / "__init__.py", "")
    write_file(dest / "config" / "settings" / "base.py", tmpl.render_settings_base(ctx))
    write_file(dest / "config" / "settings" / "development.py", tmpl.render_settings_dev(ctx))
    write_file(dest / "config" / "settings" / "production.py", tmpl.render_settings_prod(ctx))
    write_file(dest / "config" / "urls.py", tmpl.render_urls(ctx))
    write_file(dest / "config" / "wsgi.py", tmpl.render_wsgi(ctx))
    write_file(dest / "config" / "asgi.py", tmpl.render_asgi(ctx))

    # apps/ — user-added Django apps live here
    write_file(dest / "apps" / "__init__.py", "")

    # templates/ placeholder
    write_file(dest / "templates" / ".gitkeep", "")

    # static/ placeholder
    write_file(dest / "static" / ".gitkeep", "")

    # .env files
    write_file(dest / ".env", tmpl.render_env(ctx, example=False))
    write_file(dest / ".env.example", tmpl.render_env(ctx, example=True))

    # requirements.txt — pin exact version for reproducible installs
    write_file(dest / "requirements.txt", f"webapptemplate=={webapptemplate.__version__}\n")

    # .gitignore
    write_file(dest / ".gitignore", tmpl.render_gitignore(ctx))

    # README and CLAUDE.md
    write_file(dest / "README.md", tmpl.render_readme(ctx))
    write_file(dest / "CLAUDE.md", tmpl.render_claude_md(ctx))

    # Docker files (optional)
    if use_docker:
        write_file(dest / ".dockerignore", tmpl.render_dockerignore(ctx))
        write_file(dest / "Dockerfile", tmpl.render_dockerfile(ctx))
        write_file(dest / "docker-compose.yml", tmpl.render_docker_compose(ctx))
        write_file(dest / "docker-compose.dev.yml", tmpl.render_docker_compose_dev(ctx))
