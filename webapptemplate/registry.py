"""
Nav item and URL registry for webapptemplate.

Project apps register nav items and URL patterns by subclassing WebAppConfig
in their apps.py. This module is the single source of truth for those
registrations at runtime.
"""

_nav_items: list[dict] = []
_url_entries: list[dict] = []  # {"prefix": ..., "module": ..., "app_config": ...}
_api_routers: list[dict] = []  # {"prefix": ..., "router": ...}


def register_nav_item(url: str, label: str, icon: str, order: int = 100) -> None:
    _nav_items.append({"url": url, "label": label, "icon": icon, "order": order})
    _nav_items.sort(key=lambda x: (x["order"], x["label"]))


def register_urls(prefix: str, module: str) -> None:
    _url_entries.append({"prefix": prefix, "module": module})


def register_api_router(prefix: str, router) -> None:
    _api_routers.append({"prefix": prefix, "router": router})


def get_nav_items() -> list[dict]:
    return list(_nav_items)


def get_url_entries() -> list[dict]:
    return list(_url_entries)


def get_api_routers() -> list[dict]:
    return list(_api_routers)
