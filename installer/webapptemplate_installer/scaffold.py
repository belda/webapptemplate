"""
Project scaffolding logic for `webapptemplate init`.
"""
import os
import re
import sys
import secrets
from pathlib import Path

from webapptemplate_installer import templates as tmpl


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

    # 1. Project name
    project_name = prompt("Project name (Python identifier, e.g. myapp)")
    project_name = slugify(project_name)
    if not project_name:
        print("Invalid project name.")
        sys.exit(1)

    # 2. Database
    db_choice = prompt(
        "Database backend",
        default="postgresql",
        choices=["postgresql", "sqlite"],
    )
    use_postgres = db_choice == "postgresql"

    # 3. Redis
    use_redis = prompt_bool("Include Redis (cache / sessions)?", default=True)

    # 4. Domain
    domain = prompt("Production domain (e.g. myapp.com)", default=f"{project_name}.com")

    # 5. Admin email
    admin_email = prompt("Admin email address", default=f"admin@{domain}")

    # 6. Docker
    use_docker = prompt_bool("Generate Dockerfile + docker-compose.yml?", default=True)

    # 7. Secret key (auto-generated, shown to user)
    secret_key = generate_secret_key()
    print(f"\n  Auto-generated SECRET_KEY: {secret_key}")
    print("  (saved to .env — keep it secret)\n")

    # Collect config
    ctx = {
        "project_name": project_name,
        "use_postgres": use_postgres,
        "use_redis": use_redis,
        "domain": domain,
        "admin_email": admin_email,
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
    p = ctx["project_name"]
    use_postgres = ctx["use_postgres"]
    use_redis = ctx["use_redis"]
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

    # apps/ placeholder
    write_file(dest / "apps" / ".gitkeep", "")

    # templates/ placeholder
    write_file(dest / "templates" / ".gitkeep", "")

    # static/ placeholder
    write_file(dest / "static" / ".gitkeep", "")

    # .env files
    write_file(dest / ".env", tmpl.render_env(ctx, example=False))
    write_file(dest / ".env.example", tmpl.render_env(ctx, example=True))

    # requirements.txt
    write_file(dest / "requirements.txt", "webapptemplate>=0.1.0\n")

    # .gitignore
    write_file(dest / ".gitignore", tmpl.render_gitignore(ctx))

    # README
    write_file(dest / "README.md", tmpl.render_readme(ctx))

    # Docker files (optional)
    if use_docker:
        write_file(dest / "Dockerfile", tmpl.render_dockerfile(ctx))
        write_file(dest / "docker-compose.yml", tmpl.render_docker_compose(ctx))
        if use_redis:
            write_file(dest / "docker-compose.dev.yml", tmpl.render_docker_compose_dev(ctx))
