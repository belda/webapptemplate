import threading

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from allauth.account.signals import user_signed_up

User = get_user_model()

# Thread-local used by AutoRegisterLoginForm to communicate registration intent
# to this signal without coupling the two via function arguments.
#
#   skip_workspace   – True when the user is registering via an invite link;
#                      the signal skips workspace creation entirely.
#   workspace_name   – Override for the new workspace name (set to the user's
#                      email address for auto-registered non-invite users).
_registration_local = threading.local()


@receiver(post_save, sender=User)
def create_default_workspace(sender, instance, created, **kwargs):
    """Create a personal workspace for every new user.

    Skipped when the user registers via an invite link (they will join the
    invited workspace instead).  The workspace is named after the user's email
    address when the account was created via the auto-registration path,
    otherwise the display name is used.
    """
    if not created:
        return
    if getattr(_registration_local, "skip_workspace", False):
        return

    from webapptemplate.apps.workspaces.models import Workspace, Membership

    workspace_name = getattr(_registration_local, "workspace_name", None)
    if not workspace_name:
        workspace_name = f"{instance.display_name}'s Workspace"

    workspace = Workspace.objects.create(
        name=workspace_name,
        owner=instance,
    )
    Membership.objects.create(
        user=instance,
        workspace=workspace,
        role=Membership.ROLE_OWNER,
    )
    instance.current_workspace = workspace
    instance.save(update_fields=["current_workspace"])


@receiver(user_signed_up)
def verify_email_on_invite_signup(sender, request, user, **kwargs):
    """
    When a new user registers by following an invitation link, their email is
    already proven — mark it verified immediately so they are never blocked by
    the email-verification gate and land directly inside the invited workspace.
    """
    token = request.session.get("pending_invite_token")
    if not token:
        return

    from webapptemplate.apps.workspaces.models import Invitation
    try:
        invitation = Invitation.objects.get(token=token, accepted_at__isnull=True, email=user.email)
    except Invitation.DoesNotExist:
        return

    # invitation.email == user.email confirmed above
    from allauth.account.models import EmailAddress
    EmailAddress.objects.update_or_create(
        user=user,
        email=user.email,
        defaults={"verified": True, "primary": True},
    )
