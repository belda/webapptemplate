from django.utils.functional import SimpleLazyObject


def get_current_workspace(request):
    if not request.user.is_authenticated:
        return None
    user = request.user
    if user.current_workspace_id:
        # Verify the user is still a member
        from webapptemplate.apps.workspaces.models import Membership
        if Membership.objects.filter(user=user, workspace_id=user.current_workspace_id).exists():
            return user.current_workspace
    # Fallback: pick the first workspace they belong to
    from webapptemplate.apps.workspaces.models import Membership
    membership = Membership.objects.filter(user=user).select_related("workspace").first()
    if membership:
        user.current_workspace = membership.workspace
        user.save(update_fields=["current_workspace"])
        return membership.workspace
    return None


class CurrentWorkspaceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.workspace = SimpleLazyObject(lambda: get_current_workspace(request))
        return self.get_response(request)
