"""
Tests that verify overridden auth templates inherit from the expected base
templates, ensuring CSS, HTMX headers, and other base-level features are
present on every rendered page.
"""
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(REQUIRE_EMAIL_VERIFICATION=False)
class AuthTemplateInheritanceTest(TestCase):
    """Auth pages must extend layouts/auth.html which extends base.html."""

    def _assert_base_html_markers(self, response):
        """Check for markers that only appear if base.html was rendered."""
        content = response.content.decode()
        # HTMX header injected on <body> in base.html
        self.assertIn("hx-headers", content, "base.html body hx-headers missing")
        # CSRF meta tag added in base.html
        self.assertIn('name="csrf-token"', content, "base.html csrf-token meta tag missing")
        # Tailwind CDN loaded in base.html
        self.assertIn("cdn.tailwindcss.com", content, "Tailwind CDN missing — base.html not rendered")
        # Font Awesome loaded in base.html
        self.assertIn("fontawesome", content, "Font Awesome CDN missing — base.html not rendered")

    def _assert_auth_layout_markers(self, response):
        """Check for markers that only appear if layouts/auth.html was rendered."""
        content = response.content.decode()
        # auth.html wraps content in a centred card with this outer div
        self.assertIn(
            "min-h-full flex flex-col justify-center",
            content,
            "auth layout (layouts/auth.html) not rendered",
        )

    def test_login_page_extends_base(self):
        response = self.client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)
        self._assert_base_html_markers(response)
        self._assert_auth_layout_markers(response)

    def test_signup_page_extends_base(self):
        response = self.client.get(reverse("account_signup"))
        self.assertEqual(response.status_code, 200)
        self._assert_base_html_markers(response)
        self._assert_auth_layout_markers(response)

    def test_password_reset_page_extends_base(self):
        response = self.client.get(reverse("account_reset_password"))
        self.assertEqual(response.status_code, 200)
        self._assert_base_html_markers(response)
        self._assert_auth_layout_markers(response)

    def test_login_page_has_csrf_token_in_form(self):
        """Login form must include {% csrf_token %} for non-HTMX POST."""
        response = self.client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("csrfmiddlewaretoken", content, "login form is missing {% csrf_token %}")

    def test_signup_page_has_csrf_token_in_form(self):
        response = self.client.get(reverse("account_signup"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("csrfmiddlewaretoken", content, "signup form is missing {% csrf_token %}")


@override_settings(REQUIRE_EMAIL_VERIFICATION=False, APP_NAME="TestApp")
class AppNameInTemplatesTest(TestCase):
    """APP_NAME from settings must be rendered on every page via context processor."""

    def test_login_page_shows_app_name(self):
        response = self.client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TestApp")

    def test_signup_page_shows_app_name(self):
        response = self.client.get(reverse("account_signup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TestApp")
