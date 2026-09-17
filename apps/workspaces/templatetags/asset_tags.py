import os

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def asset(path: str) -> str:
    """Static URL with a dev cache-buster.

    In DEBUG the source file's mtime is appended as `?v=…`, so an edited
    script/stylesheet is refetched even on browsers that can't hard-refresh
    (mobile). In production filenames are already content-hashed by the
    manifest storage, so this returns the plain hashed URL unchanged.
    """
    url = static(path)
    if not settings.DEBUG:
        return url
    located = finders.find(path)
    if not located:
        return url
    try:
        stamp = int(os.path.getmtime(located))
    except OSError:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}v={stamp}"
