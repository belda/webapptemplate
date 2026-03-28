from django.urls import path
from . import views

urlpatterns = [
    path(
        "email-verification-pending/",
        views.verification_pending,
        name="email_verification_pending",
    ),
    path("settings/profile/", views.profile_settings, name="profile_settings"),
]
