from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.conf import settings
from django.views.decorators.http import require_POST

from .decorators import workspace_admin_required
from .forms import APIKeyForm, InviteForm, WorkspaceForm
from .models import APIKey, Invitation, Membership, Workspace


@login_required
def workspace_list(request):
    memberships = (
        Membership.objects.filter(user=request.user)
        .select_related("workspace")
        .order_by("workspace__name")
    )
    return render(request, "workspaces/list.html", {"memberships": memberships})


@login_required
def workspace_create(request):
    if request.method == "POST":
        form = WorkspaceForm(request.POST)
        if form.is_valid():
            workspace = form.save(commit=False)
            workspace.owner = request.user
            workspace.save()
            Membership.objects.create(
                user=request.user,
                workspace=workspace,
                role=Membership.ROLE_OWNER,
            )
            request.user.current_workspace = workspace
            request.user.save(update_fields=["current_workspace"])
            messages.success(request, f'Workspace "{workspace.name}" created.')
            if request.headers.get("HX-Request"):
                response = HttpResponse(status=204)
                response["HX-Redirect"] = "/dashboard/"
                return response
            return redirect("dashboard")
    else:
        form = WorkspaceForm()

    if request.headers.get("HX-Request"):
        return render(request, "workspaces/partials/create_form.html", {"form": form})
    return render(request, "workspaces/create.html", {"form": form})


@login_required
def workspace_switch(request, slug):
    workspace = get_object_or_404(Workspace, slug=slug)
    if not Membership.objects.filter(user=request.user, workspace=workspace).exists():
        messages.error(request, "You are not a member of that workspace.")
        return redirect("dashboard")
    request.user.current_workspace = workspace
    request.user.save(update_fields=["current_workspace"])
    if request.headers.get("HX-Request"):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = "/dashboard/"
        return response
    return redirect("dashboard")


@login_required
def workspace_settings(request):
    workspace = request.workspace
    if not workspace:
        return redirect("workspace_create")

    try:
        membership = Membership.objects.get(user=request.user, workspace=workspace)
    except Membership.DoesNotExist:
        return redirect("dashboard")

    if request.method == "POST" and membership.is_admin:
        form = WorkspaceForm(request.POST, instance=workspace)
        if form.is_valid():
            form.save()
            messages.success(request, "Workspace updated.")
            return redirect("workspace_settings")
    else:
        form = WorkspaceForm(instance=workspace)

    members = workspace.get_members()
    pending_invitations = workspace.invitations.filter(accepted_at__isnull=True)
    invite_form = InviteForm()
    members_can_invite = getattr(settings, "WORKSPACE_MEMBERS_CAN_INVITE", False)
    can_invite = membership.is_admin or members_can_invite
    use_api = getattr(settings, "USE_API", False)
    api_keys = workspace.api_keys.select_related("created_by").order_by("-created_at") if use_api else []

    return render(
        request,
        "workspaces/settings.html",
        {
            "workspace": workspace,
            "form": form,
            "members": members,
            "pending_invitations": pending_invitations,
            "invite_form": invite_form,
            "membership": membership,
            "can_invite": can_invite,
            "use_api": use_api,
            "api_keys": api_keys,
            "api_key_form": APIKeyForm(),
        },
    )


@login_required
def workspace_invite(request):
    workspace = request.workspace
    if not workspace:
        return redirect("dashboard")

    try:
        membership = Membership.objects.get(user=request.user, workspace=workspace)
        members_can_invite = getattr(settings, "WORKSPACE_MEMBERS_CAN_INVITE", False)
        if not membership.is_admin and not members_can_invite:
            messages.error(request, "Only admins can invite members.")
            return redirect("workspace_settings")
    except Membership.DoesNotExist:
        return redirect("dashboard")

    if request.method == "POST":
        form = InviteForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]

            # Don't invite existing members
            if Membership.objects.filter(workspace=workspace, user__email=email).exists():
                if request.headers.get("HX-Request"):
                    return HttpResponse('<p class="text-red-500">That person is already a member.</p>')
                messages.error(request, "That person is already a member.")
                return redirect("workspace_settings")

            invitation, created = Invitation.objects.get_or_create(
                workspace=workspace,
                email=email,
                defaults={"invited_by": request.user},
            )
            if not created:
                invitation.invited_by = request.user
                invitation.accepted_at = None
                # Reset expiry so the resent invite gets a fresh window
                from .models import INVITATION_EXPIRY_DAYS
                invitation.expires_at = timezone.now() + timedelta(days=INVITATION_EXPIRY_DAYS)
                invitation.save()

            # Send invitation email
            invite_url = request.build_absolute_uri(
                f"/workspaces/accept-invite/{invitation.token}/"
            )
            send_mail(
                subject=f"You're invited to {workspace.name}",
                message=(
                    f"{request.user.display_name} has invited you to join "
                    f'"{workspace.name}".\n\nAccept here: {invite_url}'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True,
            )

            if request.headers.get("HX-Request"):
                pending = workspace.invitations.filter(accepted_at__isnull=True)
                return render(
                    request,
                    "workspaces/partials/pending_invitations.html",
                    {"pending_invitations": pending, "workspace": workspace},
                )
            messages.success(request, f"Invitation sent to {email}.")
            return redirect("workspace_settings")

    return redirect("workspace_settings")


def accept_invitation(request, token):
    invitation = get_object_or_404(Invitation, token=token, accepted_at__isnull=True)

    if invitation.is_expired:
        messages.error(request, "This invitation has expired. Please ask a workspace admin to send a new one.")
        return redirect("dashboard") if request.user.is_authenticated else redirect("account_login")

    if not request.user.is_authenticated:
        # Store token and email in session as fallback in case the ?next= param
        # is lost during the signup/login flow.
        request.session["pending_invite_token"] = str(token)
        request.session["pending_invite_email"] = invitation.email

        # Send existing users to login, new users to signup — avoids the
        # "already registered" error when the invited email has an account.
        from urllib.parse import urlencode
        from django.contrib.auth import get_user_model
        User = get_user_model()
        base = "/accounts/login/" if User.objects.filter(email=invitation.email).exists() else "/accounts/signup/"
        qs = urlencode({"next": request.get_full_path(), "email": invitation.email})
        return redirect(f"{base}?{qs}")

    if request.user.email != invitation.email:
        messages.error(request, "This invitation was sent to a different email address.")
        return redirect("dashboard")

    Membership.objects.get_or_create(
        user=request.user,
        workspace=invitation.workspace,
        defaults={"role": Membership.ROLE_MEMBER},
    )
    invitation.accepted_at = timezone.now()
    invitation.save()

    request.user.current_workspace = invitation.workspace
    request.user.save(update_fields=["current_workspace"])

    # Accepting an invitation proves ownership of the email — mark it verified
    # so the user isn't blocked by the email-verification gate.
    from allauth.account.models import EmailAddress
    EmailAddress.objects.update_or_create(
        user=request.user,
        email=request.user.email,
        defaults={"verified": True, "primary": True},
    )

    # Clear the session invite keys now that the invite is accepted
    request.session.pop("pending_invite_token", None)
    request.session.pop("pending_invite_email", None)

    messages.success(request, f"Welcome to {invitation.workspace.name}!")
    return redirect("dashboard")


@require_POST
@login_required
def remove_member(request, membership_id):
    workspace = request.workspace
    if not workspace:
        return redirect("dashboard")
    # Scope the lookup to the current workspace to prevent cross-workspace IDOR
    membership = get_object_or_404(Membership, id=membership_id, workspace=workspace)

    try:
        requester = Membership.objects.get(user=request.user, workspace=workspace)
    except Membership.DoesNotExist:
        return redirect("dashboard")

    if not requester.is_owner:
        messages.error(request, "Only the workspace owner can remove members.")
        return redirect("workspace_settings")

    if membership.role == Membership.ROLE_OWNER:
        messages.error(request, "The workspace owner cannot be removed.")
        return redirect("workspace_settings")

    membership.delete()

    if request.headers.get("HX-Request"):
        members = workspace.get_members()
        return render(
            request,
            "workspaces/partials/members_list.html",
            {"members": members, "workspace": workspace, "membership": requester},
        )
    messages.success(request, "Member removed.")
    return redirect("workspace_settings")


@require_POST
@login_required
def cancel_invitation(request, invitation_id):
    workspace = request.workspace
    if not workspace:
        return redirect("dashboard")
    # Scope the lookup to the current workspace to prevent cross-workspace IDOR
    invitation = get_object_or_404(Invitation, id=invitation_id, workspace=workspace)

    try:
        requester = Membership.objects.get(user=request.user, workspace=workspace)
    except Membership.DoesNotExist:
        return redirect("dashboard")

    if not requester.is_admin:
        messages.error(request, "Only admins can cancel invitations.")
        return redirect("workspace_settings")

    invitation.delete()

    if request.headers.get("HX-Request"):
        pending = workspace.invitations.filter(accepted_at__isnull=True)
        return render(
            request,
            "workspaces/partials/pending_invitations.html",
            {"pending_invitations": pending, "workspace": workspace},
        )
    messages.success(request, "Invitation cancelled.")
    return redirect("workspace_settings")


@require_POST
@login_required
def transfer_ownership(request, membership_id):
    workspace = request.workspace
    if not workspace:
        return redirect("dashboard")

    target_membership = get_object_or_404(Membership, id=membership_id, workspace=workspace)

    try:
        requester = Membership.objects.get(user=request.user, workspace=workspace)
    except Membership.DoesNotExist:
        return redirect("dashboard")

    if not requester.is_owner:
        messages.error(request, "Only the workspace owner can transfer ownership.")
        return redirect("workspace_settings")

    if target_membership.role == Membership.ROLE_OWNER:
        messages.error(request, "That member is already the owner.")
        return redirect("workspace_settings")

    # Demote current owner to member, promote target to owner
    requester.role = Membership.ROLE_MEMBER
    requester.save(update_fields=["role"])

    target_membership.role = Membership.ROLE_OWNER
    target_membership.save(update_fields=["role"])

    workspace.owner = target_membership.user
    workspace.save(update_fields=["owner"])

    messages.success(request, f"Ownership transferred to {target_membership.user.display_name}.")
    if request.headers.get("HX-Request"):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = "/workspaces/settings/"
        return response
    return redirect("workspace_settings")


def _api_keys_partial(request, workspace, new_key=None):
    api_keys = workspace.api_keys.select_related("created_by").order_by("-created_at")
    return render(
        request,
        "workspaces/partials/api_keys_list.html",
        {"api_keys": api_keys, "workspace": workspace, "new_key": new_key},
    )


@require_POST
@login_required
def api_key_create(request):
    workspace = request.workspace
    if not workspace:
        return redirect("dashboard")

    try:
        membership = Membership.objects.get(user=request.user, workspace=workspace)
    except Membership.DoesNotExist:
        return redirect("dashboard")

    if not membership.is_admin:
        messages.error(request, "Only admins can create API keys.")
        return redirect("workspace_settings")

    form = APIKeyForm(request.POST)
    if not form.is_valid():
        if request.headers.get("HX-Request"):
            return _api_keys_partial(request, workspace)
        return redirect("workspace_settings")

    raw_key, prefix, key_hash = APIKey.generate()
    APIKey.objects.create(
        workspace=workspace,
        created_by=request.user,
        name=form.cleaned_data["name"],
        key_prefix=prefix,
        key_hash=key_hash,
    )

    if request.headers.get("HX-Request"):
        return _api_keys_partial(request, workspace, new_key=raw_key)
    messages.success(request, f"API key created. Copy it now — it won't be shown again.\n{raw_key}")
    return redirect("workspace_settings")


@require_POST
@login_required
def api_key_rename(request, key_id):
    workspace = request.workspace
    if not workspace:
        return redirect("dashboard")

    api_key = get_object_or_404(APIKey, id=key_id, workspace=workspace)

    try:
        membership = Membership.objects.get(user=request.user, workspace=workspace)
    except Membership.DoesNotExist:
        return redirect("dashboard")

    if not membership.is_admin:
        messages.error(request, "Only admins can rename API keys.")
        return redirect("workspace_settings")

    form = APIKeyForm(request.POST)
    if form.is_valid():
        api_key.name = form.cleaned_data["name"]
        api_key.save(update_fields=["name"])

    if request.headers.get("HX-Request"):
        return _api_keys_partial(request, workspace)
    messages.success(request, "API key renamed.")
    return redirect("workspace_settings")


@require_POST
@login_required
def api_key_delete(request, key_id):
    workspace = request.workspace
    if not workspace:
        return redirect("dashboard")

    api_key = get_object_or_404(APIKey, id=key_id, workspace=workspace)

    try:
        membership = Membership.objects.get(user=request.user, workspace=workspace)
    except Membership.DoesNotExist:
        return redirect("dashboard")

    if not membership.is_admin:
        messages.error(request, "Only admins can revoke API keys.")
        return redirect("workspace_settings")

    api_key.delete()

    if request.headers.get("HX-Request"):
        return _api_keys_partial(request, workspace)
    messages.success(request, "API key revoked.")
    return redirect("workspace_settings")
