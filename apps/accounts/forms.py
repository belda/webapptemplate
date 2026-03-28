from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        # Email is intentionally excluded: changes must go through allauth's
        # verified email-change flow at /accounts/email/ to prevent unverified
        # email addresses from being associated with an account.
        fields = ("first_name", "last_name")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "input"}),
            "last_name": forms.TextInput(attrs={"class": "input"}),
        }
