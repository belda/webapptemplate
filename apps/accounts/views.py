from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse

from allauth.account.models import EmailAddress
from allauth.account.internal.flows.email_verification import send_verification_email_for_user

from .forms import ProfileForm


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "landing.html")


@login_required
def dashboard(request):
    return render(request, "dashboard.html")


@login_required
def verification_pending(request):
    """
    Holding page shown to email/password registrants until they confirm
    their address. Already-verified users are bounced to the dashboard.
    POST resends the confirmation email.
    """
    if EmailAddress.objects.filter(user=request.user, verified=True).exists():
        return redirect("dashboard")

    if request.method == "POST":
        send_verification_email_for_user(request, request.user)
        messages.success(
            request,
            "Verification email resent — please check your inbox (and spam folder).",
        )
        return redirect("email_verification_pending")

    # Auto-send on first visit so the user doesn't have to click "Resend"
    if not request.session.get("verification_email_sent"):
        send_verification_email_for_user(request, request.user)
        request.session["verification_email_sent"] = True

    return render(
        request,
        "account/email_verification_pending.html",
        {"email": request.user.email},
    )


@login_required
def profile_settings(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            if request.headers.get("HX-Request"):
                return HttpResponse(
                    status=204,
                    headers={"HX-Redirect": reverse("profile_settings")},
                )
            return redirect("profile_settings")
    else:
        form = ProfileForm(instance=request.user)

    return render(request, "accounts/profile_settings.html", {"form": form})
