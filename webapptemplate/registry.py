"""
Nav item, URL, and settings panel registry for webapptemplate.

Project apps register nav items, URL patterns, and settings panels by
subclassing WebAppConfig in their apps.py. This module is the single
source of truth for those registrations at runtime.
"""

_nav_items: list[dict] = []
_url_entries: list[dict] = []  # {"prefix": ..., "module": ..., "app_config": ...}
_api_routers: list[dict] = []  # {"prefix": ..., "router": ...}
_workspace_settings_panels: list = []  # WorkspaceSettingsPanel instances
_user_settings_panels: list = []       # UserSettingsPanel instances


def register_nav_item(url: str, label: str, icon: str, order: int = 100) -> None:
    _nav_items.append({"url": url, "label": label, "icon": icon, "order": order})
    _nav_items.sort(key=lambda x: (x["order"], x["label"]))


def register_urls(prefix: str, module: str) -> None:
    _url_entries.append({"prefix": prefix, "module": module})


def register_api_router(prefix: str, router) -> None:
    _api_routers.append({"prefix": prefix, "router": router})


def register_workspace_settings_panel(panel) -> None:
    _workspace_settings_panels.append(panel)
    _workspace_settings_panels.sort(key=lambda p: (p.order, p.title))


def register_user_settings_panel(panel) -> None:
    _user_settings_panels.append(panel)
    _user_settings_panels.sort(key=lambda p: (p.order, p.title))


def get_nav_items() -> list[dict]:
    return list(_nav_items)


def get_url_entries() -> list[dict]:
    return list(_url_entries)


def get_api_routers() -> list[dict]:
    return list(_api_routers)


def get_workspace_settings_panels() -> list:
    return list(_workspace_settings_panels)


def get_user_settings_panels() -> list:
    return list(_user_settings_panels)
