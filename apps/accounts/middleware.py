from django.conf import settings
from django.shortcuts import redirect


# URL prefixes that unverified-but-logged-in users may always access.
# This covers all allauth auth-flow pages (login, signup, password reset,
# email confirmation, OAuth callbacks) plus admin and API.
_EXEMPT_PREFIXES = (
    "/accounts/login/",
    "/accounts/logout/",
    "/accounts/signup/",
    "/accounts/confirm-email/",
    "/accounts/email/",
    "/accounts/password/",
    "/accounts/social/",
    "/accounts/google/",
    "/accounts/email-verification-pending/",
    "/workspaces/accept-invite/",
    "/admin/",
    "/api/",
)


class EmailVerificationMiddleware:
    """
    Intercepts authenticated users whose email is not yet verified and
    redirects them to a holding page until they confirm their address.

    Only active when settings.REQUIRE_EMAIL_VERIFICATION is True.
    Social-auth users (Google etc.) are always treated as verified because
    allauth marks their EmailAddress records as verified on sign-in.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            getattr(settings, "REQUIRE_EMAIL_VERIFICATION", True)
            and request.user.is_authenticated
            and not self._is_exempt(request.path)
        ):
            if not self._has_verified_email(request.user):
                return redirect("email_verification_pending")

        return self.get_response(request)

    def _is_exempt(self, path):
        return any(path.startswith(prefix) for prefix in _EXEMPT_PREFIXES)

    def _has_verified_email(self, user):
        from allauth.account.models import EmailAddress

        return EmailAddress.objects.filter(user=user, verified=True).exists()
