from django.urls import path
from . import views

urlpatterns = [
    path("", views.workspace_list, name="workspace_list"),
    path("create/", views.workspace_create, name="workspace_create"),
    path("switch/<slug:slug>/", views.workspace_switch, name="workspace_switch"),
    path("settings/", views.workspace_settings, name="workspace_settings"),
    path("invite/", views.workspace_invite, name="workspace_invite"),
    path("accept-invite/<uuid:token>/", views.accept_invitation, name="accept_invitation"),
    path("members/<int:membership_id>/remove/", views.remove_member, name="remove_member"),
    path("invitations/<int:invitation_id>/cancel/", views.cancel_invitation, name="cancel_invitation"),
    path("members/<int:membership_id>/transfer-ownership/", views.transfer_ownership, name="transfer_ownership"),
    path("api-keys/create/", views.api_key_create, name="api_key_create"),
    path("api-keys/<int:key_id>/rename/", views.api_key_rename, name="api_key_rename"),
    path("api-keys/<int:key_id>/delete/", views.api_key_delete, name="api_key_delete"),
]
