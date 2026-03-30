"""
WebAppConfig — base AppConfig for project apps.

Usage in your app's apps.py::

    from webapptemplate.app_config import WebAppConfig
    from webapptemplate.settings_panels import WorkspaceSettingsPanel, UserSettingsPanel

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
        # Settings panels injected into workspace/user settings pages (no template overrides needed)
        workspace_settings_panels = [
            WorkspaceSettingsPanel(
                id="todos",
                title="Todos Settings",
                template="todos/panels/workspace_settings.html",
                form_class=TodosSettingsForm,  # ModelForm(instance=workspace)
            ),
        ]
        user_settings_panels = [
            UserSettingsPanel(
                id="todos-user",
                title="Todos Preferences",
                template="todos/panels/user_settings.html",
                form_class=TodosUserPrefsForm,  # ModelForm(instance=user)
            ),
        ]

Default values for all attributes are None / empty — the app will be installed
normally but won't add any nav items, URL patterns, API routes, or settings panels.
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
    # Settings panels — see webapptemplate/settings_panels.py for the dataclasses.
    workspace_settings_panels: list = []
    user_settings_panels: list = []

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

        for panel in self.workspace_settings_panels:
            registry.register_workspace_settings_panel(panel)

        for panel in self.user_settings_panels:
            registry.register_user_settings_panel(panel)
