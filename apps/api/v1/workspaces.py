from typing import List
from ninja import Router
from django.shortcuts import get_object_or_404

from apps.workspaces.models import Workspace, Membership, Invitation
from .schemas import WorkspaceSchema, MembershipSchema, InvitationSchema, WorkspaceCreateSchema, InviteSchema

router = Router(tags=["Workspaces"])


@router.get("/", response=List[WorkspaceSchema])
def list_workspaces(request):
    """List all workspaces the current user belongs to."""
    return [m.workspace for m in Membership.objects.filter(user=request.user).select_related("workspace")]


@router.post("/", response=WorkspaceSchema)
def create_workspace(request, data: WorkspaceCreateSchema):
    """Create a new workspace."""
    workspace = Workspace.objects.create(name=data.name, owner=request.user)
    Membership.objects.create(user=request.user, workspace=workspace, role=Membership.ROLE_OWNER)
    return workspace


@router.get("/{slug}/", response=WorkspaceSchema)
def get_workspace(request, slug: str):
    workspace = get_object_or_404(Workspace, slug=slug)
    get_object_or_404(Membership, user=request.user, workspace=workspace)
    return workspace


@router.get("/{slug}/members/", response=List[MembershipSchema])
def list_members(request, slug: str):
    workspace = get_object_or_404(Workspace, slug=slug)
    get_object_or_404(Membership, user=request.user, workspace=workspace)
    return workspace.memberships.select_related("user").all()


@router.get("/{slug}/invitations/", response=List[InvitationSchema])
def list_invitations(request, slug: str):
    workspace = get_object_or_404(Workspace, slug=slug)
    membership = get_object_or_404(Membership, user=request.user, workspace=workspace)
    if not membership.is_admin:
        return []
    return workspace.invitations.filter(accepted_at__isnull=True)
