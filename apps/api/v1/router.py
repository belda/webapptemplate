from django.conf import settings
from ninja import NinjaAPI
from ninja.security import django_auth

from webapptemplate.apps.workspaces.api_auth import APIKeyAuth
from webapptemplate.apps.workspaces.api import router as workspaces_router
from webapptemplate.apps.accounts.api import router as accounts_router

_app_name = getattr(settings, "APP_NAME", "WebApp")

api = NinjaAPI(
    title=f"{_app_name} API",
    version="1.0.0",
    description=f"REST API for {_app_name}",
    # APIKeyAuth first: an explicit Bearer token must win over a session cookie
    # that happens to be on the same request, otherwise the key's workspace
    # pinning is bypassed whenever the caller is also logged into the browser.
    auth=[APIKeyAuth(), django_auth],
)

api.add_router("/workspaces/", workspaces_router)
api.add_router("/accounts/", accounts_router)
