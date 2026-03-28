import json

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress

from apps.workspaces.models import Workspace, Membership, Invitation

User = get_user_model()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(email, password="testpass123", verified=True):
    user = User.objects.create_user(
        email=email,
        username=email.split("@")[0],
        password=password,
    )
    user.refresh_from_db()
    if verified:
        EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)
    return user


def _make_workspace(owner, name="Test Workspace"):
    ws = Workspace.objects.create(name=name, owner=owner)
    Membership.objects.create(user=owner, workspace=ws, role=Membership.ROLE_OWNER)
    owner.current_workspace = ws
    owner.save(update_fields=["current_workspace"])
    return ws


# ---------------------------------------------------------------------------
# Unauthenticated access
# ---------------------------------------------------------------------------


@override_settings(REQUIRE_EMAIL_VERIFICATION=False)
class UnauthenticatedAPITest(TestCase):
    """All API endpoints must reject unauthenticated requests."""

    def _assert_unauthorized(self, path):
        response = self.client.get(path)
        self.assertIn(
            response.status_code,
            [401, 403],
            msg=f"Expected 401 or 403 for unauthenticated GET {path}, got {response.status_code}",
        )

    def test_me_endpoint_rejects_anonymous(self):
        self._assert_unauthorized("/api/v1/accounts/me/")

    def test_workspaces_list_rejects_anonymous(self):
        self._assert_unauthorized("/api/v1/workspaces/")

    def test_workspace_detail_rejects_anonymous(self):
        owner = _make_user("anonws@example.com")
        ws = owner.current_workspace
        self._assert_unauthorized(f"/api/v1/workspaces/{ws.slug}/")

    def test_workspace_members_rejects_anonymous(self):
        owner = _make_user("anonmem@example.com")
        ws = owner.current_workspace
        self._assert_unauthorized(f"/api/v1/workspaces/{ws.slug}/members/")

    def test_workspace_invitations_rejects_anonymous(self):
        owner = _make_user("anoninv@example.com")
        ws = owner.current_workspace
        self._assert_unauthorized(f"/api/v1/workspaces/{ws.slug}/invitations/")


# ---------------------------------------------------------------------------
# Accounts API — /api/v1/accounts/
# ---------------------------------------------------------------------------


@override_settings(REQUIRE_EMAIL_VERIFICATION=False)
class AccountsMeEndpointTest(TestCase):
    def setUp(self):
        self.user = _make_user("meuser@example.com")
        self.user.first_name = "Me"
        self.user.last_name = "User"
        self.user.save()
        self.client.force_login(self.user)

    def test_me_returns_200(self):
        response = self.client.get("/api/v1/accounts/me/")
        self.assertEqual(response.status_code, 200)

    def test_me_returns_correct_email(self):
        response = self.client.get("/api/v1/accounts/me/")
        data = response.json()
        self.assertEqual(data["email"], "meuser@example.com")

    def test_me_returns_correct_names(self):
        response = self.client.get("/api/v1/accounts/me/")
        data = response.json()
        self.assertEqual(data["first_name"], "Me")
        self.assertEqual(data["last_name"], "User")

    def test_me_returns_display_name(self):
        response = self.client.get("/api/v1/accounts/me/")
        data = response.json()
        self.assertIn("display_name", data)


# ---------------------------------------------------------------------------
# Workspaces API — /api/v1/workspaces/
# ---------------------------------------------------------------------------


@override_settings(REQUIRE_EMAIL_VERIFICATION=False)
class WorkspacesListEndpointTest(TestCase):
    def setUp(self):
        self.user = _make_user("wsapi@example.com")
        # Auto-created personal workspace exists via signal
        self.client.force_login(self.user)

    def test_list_returns_200(self):
        response = self.client.get("/api/v1/workspaces/")
        self.assertEqual(response.status_code, 200)

    def test_list_includes_user_workspaces(self):
        response = self.client.get("/api/v1/workspaces/")
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)

    def test_list_scoped_to_current_user(self):
        """A second user's workspaces must not appear in the first user's list."""
        other = _make_user("otherws@example.com")
        other_ws = _make_workspace(other, "Other Private WS")

        response = self.client.get("/api/v1/workspaces/")
        data = response.json()
        slugs = [ws["slug"] for ws in data]
        self.assertNotIn(other_ws.slug, slugs)

    def test_create_workspace_via_api(self):
        import json as _json
        response = self.client.post(
            "/api/v1/workspaces/",
            data=_json.dumps({"name": "API Created WS"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "API Created WS")
        self.assertTrue(Workspace.objects.filter(name="API Created WS").exists())


@override_settings(REQUIRE_EMAIL_VERIFICATION=False)
class WorkspaceDetailEndpointTest(TestCase):
    def setUp(self):
        self.owner = _make_user("detailowner@example.com")
        self.workspace = _make_workspace(self.owner, "Detail WS")
        self.client.force_login(self.owner)

    def test_get_workspace_returns_200(self):
        response = self.client.get(f"/api/v1/workspaces/{self.workspace.slug}/")
        self.assertEqual(response.status_code, 200)

    def test_get_workspace_returns_correct_data(self):
        response = self.client.get(f"/api/v1/workspaces/{self.workspace.slug}/")
        data = response.json()
        self.assertEqual(data["slug"], self.workspace.slug)
        self.assertEqual(data["name"], "Detail WS")

    def test_non_member_cannot_access_workspace(self):
        outsider = _make_user("outside@example.com")
        self.client.force_login(outsider)
        response = self.client.get(f"/api/v1/workspaces/{self.workspace.slug}/")
        self.assertEqual(response.status_code, 404)


@override_settings(REQUIRE_EMAIL_VERIFICATION=False)
class WorkspaceMembersEndpointTest(TestCase):
    def setUp(self):
        self.owner = _make_user("memapi@example.com")
        self.workspace = _make_workspace(self.owner, "Members API WS")
        self.member = _make_user("memapimember@example.com")
        Membership.objects.create(
            user=self.member, workspace=self.workspace, role=Membership.ROLE_MEMBER
        )
        self.client.force_login(self.owner)

    def test_members_list_returns_200(self):
        response = self.client.get(f"/api/v1/workspaces/{self.workspace.slug}/members/")
        self.assertEqual(response.status_code, 200)

    def test_members_list_returns_all_members(self):
        response = self.client.get(f"/api/v1/workspaces/{self.workspace.slug}/members/")
        data = response.json()
        emails = [m["user"]["email"] for m in data]
        self.assertIn("memapi@example.com", emails)
        self.assertIn("memapimember@example.com", emails)

    def test_non_member_cannot_list_members(self):
        outsider = _make_user("memoutsider@example.com")
        self.client.force_login(outsider)
        response = self.client.get(f"/api/v1/workspaces/{self.workspace.slug}/members/")
        self.assertEqual(response.status_code, 404)


@override_settings(REQUIRE_EMAIL_VERIFICATION=False)
class WorkspaceInvitationsEndpointTest(TestCase):
    def setUp(self):
        self.owner = _make_user("invapi@example.com")
        self.workspace = _make_workspace(self.owner, "Invitations API WS")
        Invitation.objects.create(
            workspace=self.workspace,
            email="pending@example.com",
            invited_by=self.owner,
        )
        self.client.force_login(self.owner)

    def test_invitations_list_returns_200_for_admin(self):
        response = self.client.get(
            f"/api/v1/workspaces/{self.workspace.slug}/invitations/"
        )
        self.assertEqual(response.status_code, 200)

    def test_invitations_list_returns_pending_invitations(self):
        response = self.client.get(
            f"/api/v1/workspaces/{self.workspace.slug}/invitations/"
        )
        data = response.json()
        self.assertIsInstance(data, list)
        emails = [inv["email"] for inv in data]
        self.assertIn("pending@example.com", emails)

    def test_regular_member_gets_empty_list(self):
        """Non-admin members get an empty list (not 403) as per API design."""
        member = _make_user("invapimem@example.com")
        Membership.objects.create(
            user=member, workspace=self.workspace, role=Membership.ROLE_MEMBER
        )
        self.client.force_login(member)
        response = self.client.get(
            f"/api/v1/workspaces/{self.workspace.slug}/invitations/"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, [])

    def test_non_member_cannot_list_invitations(self):
        outsider = _make_user("invoutsider@example.com")
        self.client.force_login(outsider)
        response = self.client.get(
            f"/api/v1/workspaces/{self.workspace.slug}/invitations/"
        )
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# API key Bearer token authentication
# ---------------------------------------------------------------------------


@override_settings(REQUIRE_EMAIL_VERIFICATION=False, USE_API=True)
class APIKeyBearerAuthTest(TestCase):
    def setUp(self):
        from apps.workspaces.models import APIKey
        self.owner = _make_user("bearerowner@example.com")
        self.workspace = _make_workspace(self.owner, "Bearer WS")
        self.raw_key, prefix, key_hash = APIKey.generate()
        self.api_key = APIKey.objects.create(
            workspace=self.workspace,
            created_by=self.owner,
            name="Test Bearer Key",
            key_prefix=prefix,
            key_hash=key_hash,
        )

    def test_valid_key_authenticate_returns_api_key(self):
        """APIKeyAuth.authenticate should return the APIKey object for a valid token."""
        from unittest.mock import MagicMock
        from apps.api.v1.auth import APIKeyAuth
        result = APIKeyAuth().authenticate(MagicMock(), self.raw_key)
        self.assertEqual(result, self.api_key)

    def test_invalid_bearer_token_is_rejected(self):
        response = self.client.get(
            "/api/v1/workspaces/",
            HTTP_AUTHORIZATION="Bearer sk_thisisnotavalidkey",
        )
        self.assertIn(response.status_code, [401, 403])

    def test_no_auth_is_rejected(self):
        response = self.client.get("/api/v1/workspaces/")
        self.assertIn(response.status_code, [401, 403])

    def test_last_used_at_is_updated_on_authenticate(self):
        """last_used_at is stamped in APIKeyAuth.authenticate, before the endpoint runs."""
        from unittest.mock import MagicMock
        from apps.api.v1.auth import APIKeyAuth
        self.assertIsNone(self.api_key.last_used_at)
        APIKeyAuth().authenticate(MagicMock(), self.raw_key)
        self.api_key.refresh_from_db()
        self.assertIsNotNone(self.api_key.last_used_at)

    def test_revoked_key_is_rejected(self):
        self.api_key.delete()
        response = self.client.get(
            "/api/v1/workspaces/",
            HTTP_AUTHORIZATION=f"Bearer {self.raw_key}",
        )
        self.assertIn(response.status_code, [401, 403])

    def test_invalid_key_authenticate_returns_none(self):
        from unittest.mock import MagicMock
        from apps.api.v1.auth import APIKeyAuth
        result = APIKeyAuth().authenticate(MagicMock(), "sk_notavalidkey")
        self.assertIsNone(result)
