from django import forms
from .models import Workspace, Invitation


class WorkspaceForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = ("name",)
        widgets = {
            "name": forms.TextInput(attrs={"class": "input", "placeholder": "My Workspace"}),
        }


class InviteForm(forms.ModelForm):
    class Meta:
        model = Invitation
        fields = ("email",)
        widgets = {
            "email": forms.EmailInput(attrs={"class": "input", "placeholder": "colleague@example.com"}),
        }


class APIKeyForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"class": "input", "placeholder": "e.g. Production webhook"}),
    )
