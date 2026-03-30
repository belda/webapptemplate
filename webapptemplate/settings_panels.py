"""
Settings panel system for webapptemplate.

Apps can declare workspace or user settings panels via WebAppConfig:

    class BillingConfig(WebAppConfig):
        workspace_settings_panels = [
            WorkspaceSettingsPanel(
                id="billing",
                title="Billing",
                description="Manage your subscription plan.",
                template="billing/panels/workspace_settings.html",
                form_class=BillingSettingsForm,
                admin_only=True,
            )
        ]
        user_settings_panels = [
            UserSettingsPanel(
                id="notifications",
                title="Notifications",
                template="billing/panels/user_notifications.html",
                form_class=NotificationPrefsForm,
            )
        ]

Each panel gets a URL automatically:
  WorkspaceSettingsPanel → /workspaces/settings/panel/<id>/   name="settings_panel_<id>"
  UserSettingsPanel       → /accounts/settings/panel/<id>/    name="user_settings_panel_<id>"

Panels with form_class get a free generic view:
  - GET  → renders the panel template with form (instance=workspace or user)
  - POST → validates; on success returns updated template (HTMX) or redirects (full page)

Panels with view_func get full control. The view receives the request and must return
an HttpResponse. It is responsible for GET and POST handling.
The settings page uses hx-get to lazy-load view_func panels.

Panel templates receive in context:
  panel  — the WorkspaceSettingsPanel / UserSettingsPanel instance
  form   — the bound or unbound form (only for form_class panels)
  saved  — True immediately after a successful POST (form_class panels only)
"""
from dataclasses import dataclass, field


@dataclass
class WorkspaceSettingsPanel:
    id: str
    title: str
    template: str
    description: str = ""
    admin_only: bool = False
    # Provide one of form_class (auto view) or view_func (custom view).
    form_class: type | None = None
    view_func: "callable | None" = None
    order: int = 100

    @property
    def url_name(self) -> str:
        return f"settings_panel_{self.id}"

    @property
    def url_path(self) -> str:
        return f"settings/panel/{self.id}/"


@dataclass
class UserSettingsPanel:
    id: str
    title: str
    template: str
    description: str = ""
    # Provide one of form_class (auto view) or view_func (custom view).
    form_class: type | None = None
    view_func: "callable | None" = None
    order: int = 100

    @property
    def url_name(self) -> str:
        return f"user_settings_panel_{self.id}"

    @property
    def url_path(self) -> str:
        return f"settings/panel/{self.id}/"


# ---------------------------------------------------------------------------
# Generic views (used when form_class is set)
# ---------------------------------------------------------------------------

def _make_workspace_panel_view(panel: WorkspaceSettingsPanel):
    """Return a view function for a form_class-based WorkspaceSettingsPanel."""
    from django.contrib.auth.decorators import login_required
    from django.contrib import messages
    from django.core.exceptions import PermissionDenied
    from django.shortcuts import redirect, render

    @login_required
    def _view(request):
        from webapptemplate.apps.workspaces.models import Membership

        workspace = request.workspace
        if not workspace:
            return redirect("workspace_create")
        try:
            membership = Membership.objects.get(user=request.user, workspace=workspace)
        except Membership.DoesNotExist:
            return redirect("dashboard")
        if panel.admin_only and not membership.is_admin:
            raise PermissionDenied

        saved = False
        if request.method == "POST":
            form = panel.form_class(request.POST, instance=workspace)
            if form.is_valid():
                form.save()
                saved = True
                form = panel.form_class(instance=workspace)
                if not request.headers.get("HX-Request"):
                    messages.success(request, f"{panel.title} saved.")
                    return redirect("workspace_settings")
        else:
            form = panel.form_class(instance=workspace)

        return render(request, panel.template, {"panel": panel, "form": form, "saved": saved})

    return _view


def _make_user_panel_view(panel: UserSettingsPanel):
    """Return a view function for a form_class-based UserSettingsPanel."""
    from django.contrib.auth.decorators import login_required
    from django.contrib import messages
    from django.shortcuts import redirect, render

    @login_required
    def _view(request):
        user = request.user
        saved = False
        if request.method == "POST":
            form = panel.form_class(request.POST, instance=user)
            if form.is_valid():
                form.save()
                saved = True
                form = panel.form_class(instance=user)
                if not request.headers.get("HX-Request"):
                    messages.success(request, f"{panel.title} saved.")
                    return redirect("profile_settings")
        else:
            form = panel.form_class(instance=user)

        return render(request, panel.template, {"panel": panel, "form": form, "saved": saved})

    return _view


# ---------------------------------------------------------------------------
# Helpers called from framework views
# ---------------------------------------------------------------------------

def prepare_workspace_panels(request, workspace, membership):
    """
    Return a list of panel-render dicts for the workspace settings page.

    Each dict has:
      panel      — WorkspaceSettingsPanel instance
      form       — unbound form instance (form_class panels only, else None)
      htmx_load  — True when the panel should be lazy-loaded via hx-get
    """
    from webapptemplate import registry
    result = []
    for panel in registry.get_workspace_settings_panels():
        if panel.admin_only and not membership.is_admin:
            continue
        htmx_load = panel.view_func is not None
        form = panel.form_class(instance=workspace) if panel.form_class else None
        result.append({"panel": panel, "form": form, "htmx_load": htmx_load})
    return result


def prepare_user_panels(request):
    """
    Return a list of panel-render dicts for the user settings page.

    Each dict has:
      panel      — UserSettingsPanel instance
      form       — unbound form instance (form_class panels only, else None)
      htmx_load  — True when the panel should be lazy-loaded via hx-get
    """
    from webapptemplate import registry
    result = []
    for panel in registry.get_user_settings_panels():
        htmx_load = panel.view_func is not None
        form = panel.form_class(instance=request.user) if panel.form_class else None
        result.append({"panel": panel, "form": form, "htmx_load": htmx_load})
    return result
