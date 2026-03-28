import hashlib

from django.utils import timezone
from ninja.security import HttpBearer


class APIKeyAuth(HttpBearer):
    def authenticate(self, request, token):
        from apps.workspaces.models import APIKey

        key_hash = hashlib.sha256(token.encode()).hexdigest()
        try:
            api_key = APIKey.objects.select_related("workspace").get(key_hash=key_hash)
        except APIKey.DoesNotExist:
            return None

        api_key.last_used_at = timezone.now()
        api_key.save(update_fields=["last_used_at"])

        # Attach the workspace so endpoints can use request.auth.workspace
        return api_key
