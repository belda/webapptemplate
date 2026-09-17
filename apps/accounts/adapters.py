from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme


class AccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        # If the user arrived via an invitation link, take them straight there
        # after login/signup (session fallback when the ?next= param was lost).
        token = request.session.get("pending_invite_token")
        if token:
            return f"/workspaces/accept-invite/{token}/"
        # The ?next= param is lost when the user confirms via the email link
        # (a fresh request with no query string), so it's stashed in the session
        # at signup and replayed here — this covers the email-confirmation hop
        # too, since allauth's confirmation redirect falls through to this method.
        next_url = request.session.pop("post_auth_next", None)
        if next_url:
            return next_url
        return settings.LOGIN_REDIRECT_URL

    def get_signup_redirect_url(self, request):
        return self.get_login_redirect_url(request)

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        if not user.username:
            user.username = user.email.split("@")[0]
        if commit:
            user.save()
        self._stash_post_auth_next(request)
        return user

    def _stash_post_auth_next(self, request):
        next_url = request.POST.get("next") or request.GET.get("next")
        if not next_url or next_url == settings.LOGIN_REDIRECT_URL:
            return
        if url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            request.session["post_auth_next"] = next_url


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        # Pull avatar from Google profile
        extra_data = sociallogin.account.extra_data
        if not user.avatar and extra_data.get("picture"):
            user.avatar = extra_data["picture"]
            user.save(update_fields=["avatar"])
        if not user.first_name and extra_data.get("given_name"):
            user.first_name = extra_data["given_name"]
            user.last_name = extra_data.get("family_name", "")
            user.save(update_fields=["first_name", "last_name"])
        return user
