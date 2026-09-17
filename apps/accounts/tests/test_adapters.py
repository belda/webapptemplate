from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings

from webapptemplate.apps.accounts.adapters import AccountAdapter

User = get_user_model()


class PostAuthNextTest(TestCase):
    """?next= must survive the email-confirmation hop.

    Confirming via the emailed link is a fresh request with no query string, so
    the parameter is gone by the time allauth computes the redirect. The adapter
    stashes it at signup and replays it afterwards.
    """

    def setUp(self):
        self.adapter = AccountAdapter()
        self.factory = RequestFactory()

    def _request(self, data):
        request = self.factory.post("/accounts/signup/", data)
        request.session = self.client.session
        return request

    def test_next_is_stashed_and_replayed(self):
        request = self._request({"next": "/workspaces/settings/"})
        self.adapter._stash_post_auth_next(request)
        self.assertEqual(
            self.adapter.get_login_redirect_url(request), "/workspaces/settings/"
        )

    def test_replay_consumes_the_stash(self):
        request = self._request({"next": "/workspaces/settings/"})
        self.adapter._stash_post_auth_next(request)
        self.adapter.get_login_redirect_url(request)
        self.assertEqual(
            self.adapter.get_login_redirect_url(request), settings.LOGIN_REDIRECT_URL
        )

    def test_offsite_next_is_ignored(self):
        request = self._request({"next": "https://evil.example.com/steal"})
        self.adapter._stash_post_auth_next(request)
        self.assertNotIn("post_auth_next", request.session)
        self.assertEqual(
            self.adapter.get_login_redirect_url(request), settings.LOGIN_REDIRECT_URL
        )

    def test_default_target_is_not_stashed(self):
        request = self._request({"next": settings.LOGIN_REDIRECT_URL})
        self.adapter._stash_post_auth_next(request)
        self.assertNotIn("post_auth_next", request.session)

    def test_pending_invite_wins_over_next(self):
        request = self._request({"next": "/workspaces/settings/"})
        self.adapter._stash_post_auth_next(request)
        request.session["pending_invite_token"] = "abc123"
        self.assertEqual(
            self.adapter.get_login_redirect_url(request),
            "/workspaces/accept-invite/abc123/",
        )

    @override_settings(REQUIRE_EMAIL_VERIFICATION=False)
    def test_signup_flow_stashes_next(self):
        self.client.post(
            "/accounts/signup/",
            {
                "email": "nextuser@example.com",
                "password1": "s3curepassw0rd!",
                "password2": "s3curepassw0rd!",
                "next": "/workspaces/settings/",
            },
        )
        self.assertTrue(User.objects.filter(email="nextuser@example.com").exists())
