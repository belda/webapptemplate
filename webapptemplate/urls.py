"""
webapptemplate base URL patterns.

Use in your project's config/urls.py:

    from webapptemplate.urls import urlpatterns

Project app URLs and API routers declared via WebAppConfig are auto-discovered;
you only need to add patterns that don't come from a WebAppConfig subclass.
"""
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

# Auto-include URL modules registered by WebAppConfig subclasses.
for _entry in registry.get_url_entries():
    urlpatterns.append(path(_entry["prefix"], include(_entry["module"])))

if getattr(settings, "USE_API", False):
    from webapptemplate.apps.api.v1.router import api as _api

    # Auto-add routers registered by WebAppConfig subclasses.
    for _entry in registry.get_api_routers():
        _api.add_router(_entry["prefix"], _entry["router"])

    urlpatterns += [path("api/v1/", _api.urls)]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
