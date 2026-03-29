from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("webapptemplate.apps.accounts.urls")),
    path("accounts/", include("allauth.urls")),
    path("workspaces/", include("webapptemplate.apps.workspaces.urls")),
    path("", include("webapptemplate.apps.dashboard.urls")),
]

if getattr(settings, "USE_API", False):
    from webapptemplate.apps.api.v1.router import api
    urlpatterns += [path("api/v1/", api.urls)]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
