from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from webapptemplate import registry

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("accounts/", include("webapptemplate.apps.accounts.urls")),
    path("accounts/", include("allauth.urls")),
    path("workspaces/", include("webapptemplate.apps.workspaces.urls")),
    path("", include("webapptemplate.apps.dashboard.urls")),
]

# Auto-include URL modules declared via WebAppConfig subclasses.
for _entry in registry.get_url_entries():
    urlpatterns.append(path(_entry["prefix"], include(_entry["module"])))

# Auto-register settings panel URLs declared via WebAppConfig subclasses.
from webapptemplate import settings_panels as _sp  # noqa: E402

for _panel in registry.get_workspace_settings_panels():
    _view = _panel.view_func or _sp._make_workspace_panel_view(_panel)
    urlpatterns.append(path(f"workspaces/{_panel.url_path}", _view, name=_panel.url_name))

for _panel in registry.get_user_settings_panels():
    _view = _panel.view_func or _sp._make_user_panel_view(_panel)
    urlpatterns.append(path(f"accounts/{_panel.url_path}", _view, name=_panel.url_name))

if getattr(settings, "USE_API", False):
    from django.views.generic import RedirectView
    from webapptemplate.apps.api.v1.router import api
    urlpatterns += [
        path("api/v1/", api.urls),
        path("api/docs/", RedirectView.as_view(url="/api/v1/docs"), name="api_docs"),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
