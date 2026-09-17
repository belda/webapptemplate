import hashlib

from django.utils import timezone
from ninja.errors import HttpError
from ninja.security import HttpBearer


def require_key_workspace(request, workspace):
    """A workspace-pinned API key only grants access to its own workspace.

    Session-authenticated requests are unaffected. Without this, a key minted
    for one workspace reaches every *other* workspace its creator belongs to,
    because the endpoints authorise on the principal's membership alone — so a
    leaked key escalates from one workspace to all of them.

    A key whose ``workspace`` is NULL is not pinned and reaches all of its
    principal's workspaces; the downstream membership check is the authority.
    """
    from .models import APIKey

    auth = getattr(request, "auth", None)
    if (
        isinstance(auth, APIKey)
        and auth.workspace_id is not None
        and auth.workspace_id != workspace.id
    ):
        raise HttpError(403, "This API key is not authorized for this workspace.")


class APIKeyAuth(HttpBearer):
    def authenticate(self, request, token):
        from .models import APIKey

        key_hash = hashlib.sha256(token.encode()).hexdigest()
        try:
            api_key = APIKey.objects.select_related("workspace", "created_by").get(
                key_hash=key_hash
            )
        except APIKey.DoesNotExist:
            return None

        # The key acts as its creator. A key outliving a deactivated account is
        # a standing credential for someone who is no longer allowed to log in.
        principal = api_key.created_by
        if principal is None or not principal.is_active:
            return None

        api_key.last_used_at = timezone.now()
        api_key.save(update_fields=["last_used_at"])

        # Endpoints authorise off request.user (membership lookups). Under
        # Bearer auth that is AnonymousUser unless we bind the principal here.
        request.user = principal

        # Attach the key so endpoints can use request.auth.workspace.
        return api_key
