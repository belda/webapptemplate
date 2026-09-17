from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from allauth.account.models import EmailAddress

from webapptemplate.apps.workspaces.middleware import SESSION_KEY
from webapptemplate.apps.workspaces.models import Membership, Workspace

User = get_user_model()


def _make_user(email, password="testpass123"):
    user = User.objects.create_user(
        email=email, username=email.split("@")[0], password=password
    )
    user.refresh_from_db()
    EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)
    return user


def _add_workspace(user, name):
    workspace = Workspace.objects.create(name=name, owner=user)
    Membership.objects.create(user=user, workspace=workspace, role=Membership.ROLE_OWNER)
    return workspace


@override_settings(REQUIRE_EMAIL_VERIFICATION=False)
class CurrentWorkspaceSessionScopeTest(TestCase):
    """The active workspace is per-session; the account field is only a seed."""

    def setUp(self):
        self.user = _make_user("switcher@example.com")
        self.personal = self.user.current_workspace
        self.second = _add_workspace(self.user, "Second WS")

    def test_session_seeded_from_account_hint_on_first_request(self):
        self.client.force_login(self.user)
        response = self.client.get("/dashboard/")
        self.assertEqual(response.context["current_workspace"], self.personal)
        self.assertEqual(self.client.session[SESSION_KEY], self.personal.id)

    def test_switch_writes_session_and_updates_hint(self):
        self.client.force_login(self.user)
        self.client.get(f"/workspaces/switch/{self.second.slug}/")

        self.assertEqual(self.client.session[SESSION_KEY], self.second.id)
        self.user.refresh_from_db()
        self.assertEqual(self.user.current_workspace, self.second)

    def test_switch_in_one_session_does_not_move_another_session(self):
        """The regression this exists for: two logins for the same account.

        With the workspace read off `User.current_workspace`, switching in one
        browser silently moved every other logged-in session too.
        """
        first = Client()
        second = Client()
        first.force_login(self.user)
        second.force_login(self.user)

        # Both sessions start on the personal workspace.
        self.assertEqual(first.get("/dashboard/").context["current_workspace"], self.personal)
        self.assertEqual(second.get("/dashboard/").context["current_workspace"], self.personal)

        first.get(f"/workspaces/switch/{self.second.slug}/")

        self.assertEqual(first.get("/dashboard/").context["current_workspace"], self.second)
        self.assertEqual(second.get("/dashboard/").context["current_workspace"], self.personal)

    def test_session_pointing_at_lost_membership_falls_back(self):
        self.client.force_login(self.user)
        self.client.get(f"/workspaces/switch/{self.second.slug}/")
        Membership.objects.filter(user=self.user, workspace=self.second).delete()

        response = self.client.get("/dashboard/")
        self.assertEqual(response.context["current_workspace"], self.personal)

    def test_switch_to_workspace_without_membership_is_refused(self):
        outsider = _make_user("outsider@example.com")
        foreign = outsider.current_workspace

        self.client.force_login(self.user)
        self.client.get(f"/workspaces/switch/{foreign.slug}/")

        self.assertNotEqual(self.client.session.get(SESSION_KEY), foreign.id)
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.current_workspace, foreign)

    def test_anonymous_request_has_no_workspace(self):
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)
        self.assertNotIn(SESSION_KEY, self.client.session)
