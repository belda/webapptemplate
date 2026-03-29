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
    auth=[django_auth, APIKeyAuth()],
)

api.add_router("/workspaces/", workspaces_router)
api.add_router("/accounts/", accounts_router)
