from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from webapptemplate.apps.workspaces.models import Workspace, Membership, Invitation

User = get_user_model()


def _make_user(email, password="testpass123"):
    user = User.objects.create_user(
        email=email,
        username=email.split("@")[0],
        password=password,
    )
    user.refresh_from_db()
    return user


class WorkspaceModelTest(TestCase):
    def setUp(self):
        self.owner = _make_user("owner@example.com")
        self.owner.refresh_from_db()
        # The signal auto-creates a workspace; use it
        self.workspace = self.owner.current_workspace

    def test_slug_auto_generated_from_name(self):
        self.assertIsNotNone(self.workspace.slug)
        self.assertGreater(len(self.workspace.slug), 0)

    def test_slug_is_unique_when_name_collides(self):
        w1 = Workspace.objects.create(name="My Team", owner=self.owner)
        w2 = Workspace.objects.create(name="My Team", owner=self.owner)
        self.assertNotEqual(w1.slug, w2.slug)

    def test_user_role_returns_correct_role(self):
        role = self.workspace.user_role(self.owner)
        self.assertEqual(role, Membership.ROLE_OWNER)

    def test_user_role_returns_none_for_non_member(self):
        other = _make_user("other@example.com")
        role = self.workspace.user_role(other)
        self.assertIsNone(role)

    def test_get_member_count(self):
        self.assertEqual(self.workspace.get_member_count(), 1)


class MembershipModelTest(TestCase):
    def setUp(self):
        self.owner = _make_user("mowner@example.com")
        self.owner.refresh_from_db()
        self.workspace = self.owner.current_workspace
        self.membership = Membership.objects.get(user=self.owner, workspace=self.workspace)

    def test_owner_is_admin(self):
        self.assertTrue(self.membership.is_admin)

    def test_owner_is_owner(self):
        self.assertTrue(self.membership.is_owner)

    def test_member_role_not_admin(self):
        member_user = _make_user("member@example.com")
        member_user.refresh_from_db()
        m = Membership.objects.create(
            user=member_user,
            workspace=self.workspace,
            role=Membership.ROLE_MEMBER,
        )
        self.assertFalse(m.is_admin)
        self.assertFalse(m.is_owner)

    def test_admin_role_is_admin_but_not_owner(self):
        admin_user = _make_user("admin@example.com")
        admin_user.refresh_from_db()
        m = Membership.objects.create(
            user=admin_user,
            workspace=self.workspace,
            role=Membership.ROLE_ADMIN,
        )
        self.assertTrue(m.is_admin)
        self.assertFalse(m.is_owner)

    def test_unique_together_enforced(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Membership.objects.create(
                user=self.owner,
                workspace=self.workspace,
                role=Membership.ROLE_MEMBER,
            )


class InvitationModelTest(TestCase):
    def setUp(self):
        self.owner = _make_user("invowner@example.com")
        self.owner.refresh_from_db()
        self.workspace = self.owner.current_workspace

    def test_invitation_has_token(self):
        inv = Invitation.objects.create(
            workspace=self.workspace,
            email="guest@example.com",
            invited_by=self.owner,
        )
        self.assertIsNotNone(inv.token)

    def test_expires_at_auto_set(self):
        inv = Invitation.objects.create(
            workspace=self.workspace,
            email="guest2@example.com",
            invited_by=self.owner,
        )
        self.assertIsNotNone(inv.expires_at)
        # Should expire roughly 7 days from now
        delta = inv.expires_at - timezone.now()
        self.assertGreater(delta.days, 5)

    def test_is_pending_when_not_accepted(self):
        inv = Invitation.objects.create(
            workspace=self.workspace,
            email="pending@example.com",
            invited_by=self.owner,
        )
        self.assertTrue(inv.is_pending)

    def test_is_not_pending_after_acceptance(self):
        inv = Invitation.objects.create(
            workspace=self.workspace,
            email="accepted@example.com",
            invited_by=self.owner,
        )
        inv.accepted_at = timezone.now()
        inv.save()
        self.assertFalse(inv.is_pending)

    def test_is_expired_when_past_expiry(self):
        inv = Invitation.objects.create(
            workspace=self.workspace,
            email="expired@example.com",
            invited_by=self.owner,
            expires_at=timezone.now() - timedelta(days=1),
        )
        self.assertTrue(inv.is_expired)

    def test_is_not_expired_when_within_window(self):
        inv = Invitation.objects.create(
            workspace=self.workspace,
            email="fresh@example.com",
            invited_by=self.owner,
        )
        self.assertFalse(inv.is_expired)


class CreateDefaultWorkspaceSignalTest(TestCase):
    """post_save signal auto-creates a personal workspace for each new user."""

    def test_workspace_created_on_user_signup(self):
        user = _make_user("signal@example.com")
        user.refresh_from_db()
        self.assertIsNotNone(user.current_workspace)
        self.assertTrue(
            Membership.objects.filter(user=user, workspace=user.current_workspace).exists()
        )

    def test_user_is_owner_of_auto_created_workspace(self):
        user = _make_user("sigown@example.com")
        user.refresh_from_db()
        membership = Membership.objects.get(user=user, workspace=user.current_workspace)
        self.assertEqual(membership.role, Membership.ROLE_OWNER)
