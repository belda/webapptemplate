from django.conf import settings
from webapptemplate import registry


def app_settings(request):
    """Inject APP_NAME, registered nav_items, and feature flags into every template context."""
    return {
        "APP_NAME": getattr(settings, "APP_NAME", "WebApp"),
        "nav_items": registry.get_nav_items(),
        "use_api": getattr(settings, "USE_API", False),
    }
