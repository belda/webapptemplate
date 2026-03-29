"""
WebAppConfig — base AppConfig for project apps.

Usage in your app's apps.py::

    from webapptemplate.app_config import WebAppConfig

    class TodosConfig(WebAppConfig):
        name = "apps.todos"
        # Human-readable sidebar entry
        nav_items = [
            {"url": "todos:list", "label": "Todos", "icon": "list", "order": 20},
        ]
        # Auto-include apps/todos/urls.py at this URL prefix
        url_prefix = "todos/"
        # Auto-register a Ninja router (import lazily to avoid circular imports)
        # api_router_module = "apps.todos.api"   # must expose a `router` attribute
        # api_router_prefix = "/todos/"

Default values for all attributes are None / empty — the app will be installed
normally but won't add any nav items, URL patterns, or API routes automatically.
"""
from django.apps import AppConfig


class WebAppConfig(AppConfig):
    # List of dicts: {"url": str, "label": str, "icon": str, "order": int}
    nav_items: list[dict] = []
    # If set, the app's urls.py is auto-included at this prefix in wt_urlpatterns.
    url_prefix: str | None = None
    # If set, import <api_router_module>.router and add it to the NinjaAPI instance.
    api_router_module: str | None = None
    api_router_prefix: str | None = None  # defaults to "/<app_label>/"

    def ready(self) -> None:
        super().ready()
        from webapptemplate import registry

        for item in self.nav_items:
            registry.register_nav_item(**item)

        if self.url_prefix is not None:
            registry.register_urls(self.url_prefix, f"{self.name}.urls")

        if self.api_router_module is not None:
            import importlib
            mod = importlib.import_module(self.api_router_module)
            prefix = self.api_router_prefix or f"/{self.label}/"
            registry.register_api_router(prefix, mod.router)
