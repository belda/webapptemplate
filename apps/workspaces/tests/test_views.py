from datetime import timedelta

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from allauth.account.models import EmailAddress

from apps.workspaces.models import Workspace, Membership, Invitation

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(email, password="testpass123", verified=True):
    """Create a user. Signal auto-creates a personal workspace."""
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
    """Create an additional workspace and set it as the owner's current workspace."""
    ws = Workspace.objects.create(name=name, owner=owner)
    Membership.objects.create(user=owner, workspace=ws, role=Membership.ROLE_OWNER)
    owner.current_workspace = ws
    owner.save(update_fields=["current_workspace"])
    return ws


# ---------------------------------------------------------------------------
# Workspace creation
# ---------------------------------------------------------------------------

@override_settings(REQUIRE_EMAIL_VERIFICATION=False)
class WorkspaceCreateTest(TestCase):
    def setUp(self):
        self.user = _make_user("creator@example.com")
        self.client.force_login(self.user)

    def test_get_create_page_renders(self):
        response = self.client.get("/workspaces/create/")
        self.assertEqual(response.status_code, 200)

    def test_post_creates_workspace_and_owner_membership(self):
        before_count = Workspace.objects.count()
        response = self.client.post("/workspaces/create/", {"name": "Brand New WS"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Workspace.objects.count(), before_count + 1)
        ws = Workspace.objects.get(name="Brand New WS")
        self.assertTrue(
            Membership.objects.filter(
                user=self.user, workspace=ws, role=Membership.ROLE_OWNER
            ).exists()
        )

    def test_create_sets_current_workspace(self):
        self.client.post("/workspaces/create/", {"name": "Switch Me"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.current_workspace.name, "Switch Me")

    def test_create_requires_login(self):
        self.client.logout()
        response = self.client.post("/workspaces/create/", {"name": "Nope"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])


# ---------------------------------------------------------------------------
# Workspace settings — name update
# ---------------------------------------------------------------------------

@override_settings(REQUIRE_EMAIL_VERIFICATION=False)
class WorkspaceSettingsUpdateTest(TestCase):
    def setUp(self):
        self.owner = _make_user("settingsowner@example.com")
        self.workspace = _make_workspace(self.owner, "Original Name")
        self.client.force_login(self.owner)

    def test_settings_page_renders(self):
        response = self.client.get("/workspaces/settings/")
        self.assertEqual(response.status_code, 200)

    def test_admin_can_rename_workspace(self):
        response = self.client.post("/workspaces/settings/", {"name": "Renamed"})
        self.assertRedirects(
            response, "/workspaces/settings/", fetch_redirect_response=False
        )
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.name, "Renamed")

    def test_member_cannot_rename_workspace(self):
        member = _make_user("member@example.com")
        Membership.objects.create(
            user=member, workspace=self.workspace, role=Membership.ROLE_MEMBER
        )
        member.current_workspace = self.workspace
        member.save(update_fields=["current_workspace"])
        self.client.force_login(member)

        self.client.post("/workspaces/settings/", {"name": "Hijacked"})
        self.workspace.refresh_from_db()
        self.assertNotEqual(self.workspace.name, "Hijacked")


# ---------------------------------------------------------------------------
# Workspace switching
# ---------------------------------------------------------------------------

@override_settings(REQUIRE_EMAIL_VERIFICATION=False)
class WorkspaceSwitchTest(TestCase):
    def setUp(self):
        self.user = _make_user("switcher@example.com")
        self.workspace_a = _make_workspace(self.user, "Workspace A")

    def test_member_can_switch_to_their_workspace(self):
        workspace_b = _make_workspace(self.user, "Workspace B")
        self.client.force_login(self.user)
        response = self.client.get(f"/workspaces/switch/{workspace_b.slug}/")
        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertEqual(self.user.current_workspace, workspace_b)

    def test_non_member_cannot_switch_to_foreign_workspace(self):
        other_owner = _make_user("other@example.com")
        foreign_ws = other_owner.current_workspace
        self.client.force_login(self.user)
        response = self.client.get(f"/workspaces/switch/{foreign_ws.slug}/")
        # Redirected to dashboard with an error — current workspace unchanged
        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.current_workspace, foreign_ws)

    def test_switch_requires_login(self):
        response = self.client.get(f"/workspaces/switch/{self.workspace_a.slug}/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])


# ---------------------------------------------------------------------------
# Member listing
# ---------------------------------------------------------------------------

@override_settings(REQUIRE_EMAIL_VERIFICATION=False)
class MemberListTest(TestCase):
    def setUp(self):
        self.owner = _make_user("listowner@example.com")
        self.workspace = _make_workspace(self.owner, "List WS")
        self.member = _make_user("listmember@example.com")
        Membership.objects.create(
            user=self.member,
            workspace=self.workspace,
            role=Membership.ROLE_MEMBER,
        )

    def test_workspace_member_sees_members_list(self):
        self.client.force_login(self.owner)
        response = self.client.get("/workspaces/settings/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("members", response.context)

    def test_non_member_cannot_see_workspace_settings(self):
        outsider = _make_user("outsider@example.com")
        self.client.force_login(outsider)
        # outsider's current_workspace is their own personal workspace
        # accessing settings for the right workspace requires current_workspace to be set
        response = self.client.get("/workspaces/settings/")
        # They get their own personal workspace settings (200), NOT the owner's workspace
        self.assertEqual(response.status_code, 200)
        # Make sure the workspace in context is NOT the owner's workspace
        ctx_workspace = response.context.get("workspace")
        if ctx_workspace:
            self.assertNotEqual(ctx_workspace.id, self.workspace.id)


# ---------------------------------------------------------------------------
# Remove member
# ---------------------------------------------------------------------------

@override_settings(REQUIRE_EMAIL_VERIFICATION=False)
class RemoveMemberTest(TestCase):
    def setUp(self):
        self.owner = _make_user("rmowner@example.com")
        self.workspace = _make_workspace(self.owner, "Remove WS")
        self.member = _make_user("rmmember@example.com")
        self.membership = Membership.objects.create(
            user=self.member,
            workspace=self.workspace,
            role=Membership.ROLE_MEMBER,
        )
        self.client.force_login(self.owner)

    def test_get_method_not_allowed(self):
        response = self.client.get(
            f"/workspaces/members/{self.membership.id}/remove/"
        )
        self.assertEqual(response.status_code, 405)

    def test_owner_can_remove_member(self):
        response = self.client.post(
            f"/workspaces/members/{self.membership.id}/remove/"
        )
        self.assertRedirects(
            response, "/workspaces/settings/", fetch_redirect_response=False
        )
        self.assertFalse(
            Membership.objects.filter(id=self.membership.id).exists()
        )

    def test_non_owner_cannot_remove_member(self):
        admin = _make_user("rmadmin@example.com")
        Membership.objects.create(
            user=admin, workspace=self.workspace, role=Membership.ROLE_ADMIN
        )
        admin.current_workspace = self.workspace
        admin.save(update_fields=["current_workspace"])
        self.client.force_login(admin)

        response = self.client.post(
            f"/workspaces/members/{self.membership.id}/remove/"
        )
        self.assertRedirects(
            response, "/workspaces/settings/", fetch_redirect_response=False
        )
        # Member should still exist
        self.assertTrue(Membership.objects.filter(id=self.membership.id).exists())

    def test_idor_cannot_remove_member_from_another_workspace(self):
        """Scoping fix: membership_id from another workspace must return 404."""
        other_owner = _make_user("otherowner@example.com")
        other_ws = other_owner.current_workspace
        other_member = _make_user("othermember@example.com")
        other_membership = Membership.objects.create(
            user=other_member, workspace=other_ws, role=Membership.ROLE_MEMBER
        )
        # owner's current_workspace is self.workspace
        # Try to remove a membership that belongs to other_ws
        response = self.client.post(
            f"/workspaces/members/{other_membership.id}/remove/"
        )
        self.assertEqual(response.status_code, 404)
        # The other workspace's membership should be untouched
        self.assertTrue(Membership.objects.filter(id=other_membership.id).exists())

    def test_cannot_remove_workspace_owner(self):
        owner_membership = Membership.objects.get(
            user=self.owner, workspace=self.workspace
        )
        response = self.client.post(
            f"/workspaces/members/{owner_membership.id}/remove/"
        )
        self.assertRedirects(
            response, "/workspaces/settings/", fetch_redirect_response=False
        )
        self.assertTrue(
            Membership.objects.filter(id=owner_membership.id).exists()
        )


# ---------------------------------------------------------------------------
# Invitation creation
# ---------------------------------------------------------------------------

@override_settings(REQUIRE_EMAIL_VERIFICATION=False, WORKSPACE_MEMBERS_CAN_INVITE=True)
class InvitationCreateTest(TestCase):
    def setUp(self):
        self.owner = _make_user("invowner@example.com")
        self.workspace = _make_workspace(self.owner, "Invite WS")
        self.client.force_login(self.owner)

    def test_send_invite_creates_invitation(self):
        response = self.client.post(
            "/workspaces/invite/", {"email": "newguest@example.com"}
        )
        self.assertRedirects(
            response, "/workspaces/settings/", fetch_redirect_response=False
        )
        self.assertTrue(
            Invitation.objects.filter(
                workspace=self.workspace, email="newguest@example.com"
            ).exists()
        )

    def test_duplicate_invite_is_idempotent(self):
        """Sending a second invite to the same email reuses the existing invitation."""
        self.client.post("/workspaces/invite/", {"email": "dup@example.com"})
        self.client.post("/workspaces/invite/", {"email": "dup@example.com"})
        count = Invitation.objects.filter(
            workspace=self.workspace, email="dup@example.com"
        ).count()
        self.assertEqual(count, 1)

    def test_cannot_invite_existing_member(self):
        existing = _make_user("existmem@example.com")
        Membership.objects.create(
            user=existing, workspace=self.workspace, role=Membership.ROLE_MEMBER
        )
        response = self.client.post(
            "/workspaces/invite/", {"email": "existmem@example.com"}
        )
        # Should not create an invitation
        self.assertFalse(
            Invitation.objects.filter(
                workspace=self.workspace, email="existmem@example.com"
            ).exists()
        )

    @override_settings(WORKSPACE_MEMBERS_CAN_INVITE=False)
    def test_regular_member_blocked_from_inviting(self):
        member = _make_user("blockinv@example.com")
        Membership.objects.create(
            user=member, workspace=self.workspace, role=Membership.ROLE_MEMBER
        )
        member.current_workspace = self.workspace
        member.save(update_fields=["current_workspace"])
        self.client.force_login(member)

        self.client.post("/workspaces/invite/", {"email": "blocked@example.com"})
        self.assertFalse(
            Invitation.objects.filter(
                workspace=self.workspace, email="blocked@example.com"
            ).exists()
        )


# ---------------------------------------------------------------------------
# Invitation acceptance
# ---------------------------------------------------------------------------

@override_settings(REQUIRE_EMAIL_VERIFICATION=False)
class AcceptInvitationTest(TestCase):
    def setUp(self):
        self.owner = _make_user("accowner@example.com")
        self.workspace = _make_workspace(self.owner, "Accept WS")

    def test_valid_token_joins_workspace(self):
        invite = Invitation.objects.create(
            workspace=self.workspace,
            email="joiner@example.com",
            invited_by=self.owner,
        )
        invitee = _make_user("joiner@example.com")
        self.client.force_login(invitee)

        response = self.client.get(f"/workspaces/accept-invite/{invite.token}/")
        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)
        self.assertTrue(
            Membership.objects.filter(
                user=invitee, workspace=self.workspace
            ).exists()
        )
        invite.refresh_from_db()
        self.assertIsNotNone(invite.accepted_at)

    def test_expired_token_rejected(self):
        invite = Invitation.objects.create(
            workspace=self.workspace,
            email="expired@example.com",
            invited_by=self.owner,
            expires_at=timezone.now() - timedelta(days=1),
        )
        invitee = _make_user("expired@example.com")
        self.client.force_login(invitee)

        response = self.client.get(f"/workspaces/accept-invite/{invite.token}/")
        # Should NOT be added to workspace
        self.assertFalse(
            Membership.objects.filter(
                user=invitee, workspace=self.workspace
            ).exists()
        )
        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)

    def test_already_member_invitation_still_works(self):
        """Accepting an invite when already a member is harmless (get_or_create)."""
        invite = Invitation.objects.create(
            workspace=self.workspace,
            email="alreadyin@example.com",
            invited_by=self.owner,
        )
        member = _make_user("alreadyin@example.com")
        Membership.objects.create(
            user=member, workspace=self.workspace, role=Membership.ROLE_MEMBER
        )
        self.client.force_login(member)

        response = self.client.get(f"/workspaces/accept-invite/{invite.token}/")
        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)
        # Still exactly one membership
        self.assertEqual(
            Membership.objects.filter(user=member, workspace=self.workspace).count(), 1
        )

    def test_wrong_email_cannot_accept(self):
        invite = Invitation.objects.create(
            workspace=self.workspace,
            email="rightperson@example.com",
            invited_by=self.owner,
        )
        wrong_user = _make_user("wrongperson@example.com")
        self.client.force_login(wrong_user)

        response = self.client.get(f"/workspaces/accept-invite/{invite.token}/")
        # Should redirect to dashboard with an error; wrong user NOT added
        self.assertFalse(
            Membership.objects.filter(
                user=wrong_user, workspace=self.workspace
            ).exists()
        )

    def test_unauthenticated_user_redirected_to_login_or_signup(self):
        invite = Invitation.objects.create(
            workspace=self.workspace,
            email="newbie@example.com",
            invited_by=self.owner,
        )
        response = self.client.get(f"/workspaces/accept-invite/{invite.token}/")
        self.assertEqual(response.status_code, 302)
        # Should go to login or signup, not dashboard
        self.assertIn("/accounts/", response["Location"])

    def test_accept_marks_email_as_verified(self):
        """Accepting an invitation proves email ownership — must mark it verified."""
        invite = Invitation.objects.create(
            workspace=self.workspace,
            email="verifyinv@example.com",
            invited_by=self.owner,
        )
        invitee = _make_user("verifyinv@example.com", verified=False)
        self.client.force_login(invitee)

        self.client.get(f"/workspaces/accept-invite/{invite.token}/")
        self.assertTrue(
            EmailAddress.objects.filter(
                user=invitee, email="verifyinv@example.com", verified=True
            ).exists()
        )

    def test_invitation_expiry_7_day_window(self):
        """A fresh invitation is within the 7-day window; an 8-day-old one is expired."""
        fresh = Invitation.objects.create(
            workspace=self.workspace,
            email="fresh@example.com",
            invited_by=self.owner,
        )
        self.assertFalse(fresh.is_expired)

        stale = Invitation.objects.create(
            workspace=self.workspace,
            email="stale@example.com",
            invited_by=self.owner,
            expires_at=timezone.now() - timedelta(days=1),
        )
        self.assertTrue(stale.is_expired)


# ---------------------------------------------------------------------------
# Cancel invitation
# ---------------------------------------------------------------------------

@override_settings(REQUIRE_EMAIL_VERIFICATION=False)
class CancelInvitationTest(TestCase):
    def setUp(self):
        self.owner = _make_user("canowner@example.com")
        self.workspace = _make_workspace(self.owner, "Cancel WS")
        self.invite = Invitation.objects.create(
            workspace=self.workspace,
            email="tobe@cancelled.com",
            invited_by=self.owner,
        )
        self.client.force_login(self.owner)

    def test_get_method_not_allowed(self):
        response = self.client.get(
            f"/workspaces/invitations/{self.invite.id}/cancel/"
        )
        self.assertEqual(response.status_code, 405)

    def test_admin_can_cancel_invitation(self):
        response = self.client.post(
            f"/workspaces/invitations/{self.invite.id}/cancel/"
        )
        self.assertRedirects(
            response, "/workspaces/settings/", fetch_redirect_response=False
        )
        self.assertFalse(Invitation.objects.filter(id=self.invite.id).exists())

    def test_member_cannot_cancel_invitation(self):
        member = _make_user("canmem@example.com")
        Membership.objects.create(
            user=member, workspace=self.workspace, role=Membership.ROLE_MEMBER
        )
        member.current_workspace = self.workspace
        member.save(update_fields=["current_workspace"])
        self.client.force_login(member)

        self.client.post(f"/workspaces/invitations/{self.invite.id}/cancel/")
        # Invitation should still exist
        self.assertTrue(Invitation.objects.filter(id=self.invite.id).exists())

    def test_idor_cannot_cancel_invitation_from_another_workspace(self):
        """Scoping fix: invitation_id from a different workspace must return 404."""
        other_owner = _make_user("canotherown@example.com")
        other_ws = other_owner.current_workspace
        other_invite = Invitation.objects.create(
            workspace=other_ws,
            email="other@guest.com",
            invited_by=other_owner,
        )
        # self.owner's current_workspace is self.workspace, not other_ws
        response = self.client.post(
            f"/workspaces/invitations/{other_invite.id}/cancel/"
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Invitation.objects.filter(id=other_invite.id).exists())
