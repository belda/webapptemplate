from webapptemplate.apps.workspaces.models import Membership


def workspace_context(request):
    if not request.user.is_authenticated:
        return {}

    memberships = (
        Membership.objects.filter(user=request.user)
        .select_related("workspace")
        .order_by("workspace__name")
    )
    workspaces = [m.workspace for m in memberships]
    current_workspace = getattr(request, "workspace", None)

    return {
        "current_workspace": current_workspace,
        "user_workspaces": workspaces,
    }
