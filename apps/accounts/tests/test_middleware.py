from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress

User = get_user_model()


def _make_user(email, password="testpass123", verified=False):
    """Create a test user; optionally add a verified EmailAddress record."""
    user = User.objects.create_user(
        email=email,
        username=email.split("@")[0],
        password=password,
    )
    user.refresh_from_db()
    if verified:
        EmailAddress.objects.create(
            user=user, email=email, verified=True, primary=True
        )
    return user


@override_settings(REQUIRE_EMAIL_VERIFICATION=True)
class EmailVerificationMiddlewareTest(TestCase):
    """EmailVerificationMiddleware blocks unverified users and exempts specific paths."""

    # ------------------------------------------------------------------ #
    # Core blocking / passing behaviour                                   #
    # ------------------------------------------------------------------ #

    def test_unverified_user_redirected_to_pending_page(self):
        """Authenticated user with no verified email is bounced to verification-pending."""
        user = _make_user("unverified@example.com", verified=False)
        self.client.force_login(user)
        response = self.client.get("/dashboard/")
        self.assertRedirects(
            response,
            "/accounts/email-verification-pending/",
            fetch_redirect_response=False,
        )

    def test_verified_user_passes_through(self):
        """Authenticated user with a verified email can reach protected pages."""
        user = _make_user("verified@example.com", verified=True)
        self.client.force_login(user)
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_user_not_blocked_by_middleware(self):
        """Anonymous users are handled by login_required, not the verification gate."""
        response = self.client.get("/dashboard/")
        # Django's login_required redirects to /accounts/login/, not verification-pending
        self.assertRedirects(
            response,
            "/accounts/login/?next=/dashboard/",
            fetch_redirect_response=False,
        )

    # ------------------------------------------------------------------ #
    # Exempt paths                                                        #
    # ------------------------------------------------------------------ #

    def test_verification_pending_page_not_circular_redirect(self):
        """The verification-pending page itself is exempt (no infinite redirect loop)."""
        user = _make_user("loop@example.com", verified=False)
        self.client.force_login(user)
        response = self.client.get("/accounts/email-verification-pending/")
        # Must NOT be a redirect back to verification-pending
        if response.status_code == 302:
            self.assertNotIn("email-verification-pending", response["Location"])
        else:
            self.assertEqual(response.status_code, 200)

    def test_signup_path_exempt(self):
        """Signup page is exempt so unverified users can register."""
        user = _make_user("s@example.com", verified=False)
        self.client.force_login(user)
        response = self.client.get("/accounts/signup/")
        if response.status_code == 302:
            self.assertNotIn("email-verification-pending", response["Location"])

    def test_login_path_exempt(self):
        """Login page is exempt so unverified users are not bounced in a loop."""
        user = _make_user("l@example.com", verified=False)
        self.client.force_login(user)
        response = self.client.get("/accounts/login/")
        if response.status_code == 302:
            self.assertNotIn("email-verification-pending", response["Location"])

    def test_accept_invite_path_exempt(self):
        """Invitation-acceptance URL is exempt so unverified users can accept invites."""
        from apps.workspaces.models import Invitation, Workspace, Membership
        owner = _make_user("owner@example.com", verified=True)
        owner.refresh_from_db()
        workspace = owner.current_workspace
        invite = Invitation.objects.create(
            workspace=workspace,
            email="invitee@example.com",
            invited_by=owner,
        )
        # Unverified user follows the invite link
        invitee = _make_user("invitee@example.com", verified=False)
        self.client.force_login(invitee)
        response = self.client.get(f"/workspaces/accept-invite/{invite.token}/")
        # Should NOT be redirected to verification-pending
        if response.status_code == 302:
            self.assertNotIn("email-verification-pending", response["Location"])

    def test_api_path_exempt(self):
        """API paths are not subject to the email verification gate."""
        user = _make_user("api@example.com", verified=False)
        self.client.force_login(user)
        response = self.client.get("/api/v1/accounts/me/")
        if response.status_code == 302:
            self.assertNotIn("email-verification-pending", response["Location"])

    @override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
    def test_admin_path_exempt(self):
        """Admin paths are exempt from the verification gate."""
        user = _make_user("admin@example.com", verified=False)
        self.client.force_login(user)
        response = self.client.get("/admin/login/")
        if response.status_code == 302:
            self.assertNotIn("email-verification-pending", response["Location"])

    # ------------------------------------------------------------------ #
    # Setting disabled                                                    #
    # ------------------------------------------------------------------ #

    @override_settings(REQUIRE_EMAIL_VERIFICATION=False)
    def test_gate_disabled_lets_unverified_users_through(self):
        """When REQUIRE_EMAIL_VERIFICATION=False the middleware is inert."""
        user = _make_user("nogate@example.com", verified=False)
        self.client.force_login(user)
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
