from django.utils.functional import SimpleLazyObject

# The active workspace lives in the session, so it is scoped to a single login
# (one browser, one impersonation session) and never bleeds across a user's
# other devices or sessions. `User.current_workspace` is kept only as a
# per-account "last used" hint that seeds a fresh session's default — it is
# never read as the authority mid-session.
SESSION_KEY = "current_workspace_id"


def _membership_workspace(user, workspace_id):
    from webapptemplate.apps.workspaces.models import Membership

    membership = (
        Membership.objects.filter(user=user, workspace_id=workspace_id)
        .select_related("workspace")
        .first()
    )
    return membership.workspace if membership else None


def set_current_workspace(request, workspace):
    """Point *this session* at `workspace` and remember it as the login default.

    Writes the session (the authority for the active workspace) and updates the
    account-level hint used to seed the next fresh login. The hint is never read
    mid-session, so updating it here cannot yank the user's other sessions.
    """
    request.session[SESSION_KEY] = workspace.id
    if request.user.current_workspace_id != workspace.id:
        request.user.current_workspace = workspace
        request.user.save(update_fields=["current_workspace"])
    request.workspace = workspace


def get_current_workspace(request):
    if not request.user.is_authenticated:
        return None
    user = request.user

    session_id = request.session.get(SESSION_KEY)
    if session_id:
        workspace = _membership_workspace(user, session_id)
        if workspace:
            return workspace

    # Seed the session from the account's last-used hint.
    if user.current_workspace_id:
        workspace = _membership_workspace(user, user.current_workspace_id)
        if workspace:
            request.session[SESSION_KEY] = workspace.id
            return workspace

    # Final fallback: the first workspace they belong to.
    from webapptemplate.apps.workspaces.models import Membership

    membership = Membership.objects.filter(user=user).select_related("workspace").first()
    if membership:
        request.session[SESSION_KEY] = membership.workspace_id
        if user.current_workspace_id != membership.workspace_id:
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
