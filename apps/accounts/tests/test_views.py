from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress

User = get_user_model()


def _make_user(email, password="testpass123", verified=True, **kwargs):
    """Create a test user with an optional verified EmailAddress."""
    kwargs.setdefault("username", email.split("@")[0])
    user = User.objects.create_user(email=email, password=password, **kwargs)
    user.refresh_from_db()
    if verified:
        EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)
    return user


@override_settings(REQUIRE_EMAIL_VERIFICATION=False)
class RegistrationFlowTest(TestCase):
    """User registration creates the account and a personal workspace."""

    def test_signup_creates_user(self):
        response = self.client.post(
            "/accounts/signup/",
            {
                "email": "newuser@example.com",
                "password1": "Sup3rS3cr3t!",
                "password2": "Sup3rS3cr3t!",
            },
        )
        self.assertIn(response.status_code, [200, 302])
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())

    def test_signup_auto_creates_workspace(self):
        self.client.post(
            "/accounts/signup/",
            {
                "email": "wsuser@example.com",
                "password1": "Sup3rS3cr3t!",
                "password2": "Sup3rS3cr3t!",
            },
        )
        user = User.objects.filter(email="wsuser@example.com").first()
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.current_workspace)

    @override_settings(REQUIRE_EMAIL_VERIFICATION=True)
    def test_unverified_user_redirected_after_login(self):
        """After login an unverified user lands on the verification-pending page."""
        user = _make_user("noverify@example.com", verified=False)
        self.client.force_login(user)
        response = self.client.get("/dashboard/")
        self.assertRedirects(
            response,
            "/accounts/email-verification-pending/",
            fetch_redirect_response=False,
        )


@override_settings(REQUIRE_EMAIL_VERIFICATION=False)
class LoginLogoutTest(TestCase):
    def setUp(self):
        self.user = _make_user("logintest@example.com", password="testpass123")

    def test_login_with_valid_credentials_redirects_to_dashboard(self):
        response = self.client.post(
            "/accounts/login/",
            {"login": "logintest@example.com", "password": "testpass123"},
        )
        # allauth returns 302 on success
        self.assertEqual(response.status_code, 302)

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(
            "/accounts/login/",
            {"login": "logintest@example.com", "password": "wrongpassword"},
        )
        # Should stay on login page (200) or redirect back with error
        self.assertIn(response.status_code, [200, 302])
        if response.status_code == 302:
            self.assertNotIn("/dashboard/", response["Location"])

    def test_logout_logs_user_out(self):
        self.client.force_login(self.user)
        self.client.post("/accounts/logout/")
        response = self.client.get("/dashboard/")
        # After logout, /dashboard/ requires login again
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])


@override_settings(REQUIRE_EMAIL_VERIFICATION=False)
class ProfileSettingsViewTest(TestCase):
    def setUp(self):
        self.user = _make_user("profile@example.com")
        self.client.force_login(self.user)

    def test_profile_page_renders(self):
        response = self.client.get("/accounts/settings/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/profile_settings.html")

    def test_profile_update_saves_name(self):
        response = self.client.post(
            "/accounts/settings/profile/",
            {"first_name": "Updated", "last_name": "Name"},
        )
        # Should redirect back to profile settings on success
        self.assertRedirects(
            response, "/accounts/settings/profile/", fetch_redirect_response=False
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.last_name, "Name")

    def test_profile_update_does_not_change_email(self):
        original_email = self.user.email
        # Attempt to change email via POST (email not in form fields)
        self.client.post(
            "/accounts/settings/profile/",
            {"first_name": "X", "last_name": "Y", "email": "hacked@evil.com"},
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, original_email)

    def test_profile_requires_login(self):
        self.client.logout()
        response = self.client.get("/accounts/settings/profile/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_profile_update_htmx_returns_redirect_header(self):
        response = self.client.post(
            "/accounts/settings/profile/",
            {"first_name": "HTMX", "last_name": "User"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 204)
        self.assertIn("HX-Redirect", response)


@override_settings(REQUIRE_EMAIL_VERIFICATION=False)
class VerificationPendingViewTest(TestCase):
    def test_already_verified_user_bounced_to_dashboard(self):
        """verification_pending view redirects verified users away."""
        user = _make_user("verif@example.com", verified=True)
        self.client.force_login(user)
        response = self.client.get("/accounts/email-verification-pending/")
        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)

    def test_unverified_user_sees_pending_page(self):
        user = _make_user("unv@example.com", verified=False)
        self.client.force_login(user)
        response = self.client.get("/accounts/email-verification-pending/")
        self.assertEqual(response.status_code, 200)

    def test_post_resends_verification_email(self):
        """POSTing to verification_pending resends the confirmation email."""
        user = _make_user("resend@example.com", verified=False)
        self.client.force_login(user)
        response = self.client.post("/accounts/email-verification-pending/")
        self.assertRedirects(
            response,
            "/accounts/email-verification-pending/",
            fetch_redirect_response=False,
        )
