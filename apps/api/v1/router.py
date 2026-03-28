from ninja import NinjaAPI
from ninja.security import django_auth

from apps.workspaces.api_auth import APIKeyAuth
from apps.workspaces.api import router as workspaces_router
from apps.accounts.api import router as accounts_router

api = NinjaAPI(
    title="WebApp Template API",
    version="1.0.0",
    description="API for WebApp Template",
    auth=[django_auth, APIKeyAuth()],
)

api.add_router("/workspaces/", workspaces_router)
api.add_router("/accounts/", accounts_router)
