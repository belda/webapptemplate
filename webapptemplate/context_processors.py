from django.conf import settings
from webapptemplate import registry


def app_settings(request):
    """Inject APP_NAME and registered nav_items into every template context."""
    return {
        "APP_NAME": getattr(settings, "APP_NAME", "WebApp"),
        "nav_items": registry.get_nav_items(),
    }
