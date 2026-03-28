from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("email", "username", "first_name", "last_name", "is_staff", "current_workspace")
    fieldsets = UserAdmin.fieldsets + (
        ("Profile", {"fields": ("avatar", "current_workspace")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Profile", {"fields": ("email",)}),
    )
