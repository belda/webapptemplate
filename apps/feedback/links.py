from django.conf import settings


def site_base_url() -> str:
    """Absolute origin for links in outbound email, e.g. https://app.example.com.

    Emails are read outside the request that produced them, so a relative path
    is useless there. Set SITE_BASE_URL; if it is empty the path is returned
    unchanged rather than guessed at.
    """
    return (getattr(settings, "SITE_BASE_URL", "") or "").rstrip("/")


def absolute_url(path: str | None) -> str | None:
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    base = site_base_url()
    return f"{base}{path}" if base else path
