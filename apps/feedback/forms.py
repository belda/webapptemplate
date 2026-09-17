from django import forms

from .models import BugReport


# The .input component class from static/src/app.css, so these fields pick up
# whatever the project's form styling is rather than pinning their own colours.
_INPUT = "input"
_SELECT = "input"


class BugReportForm(forms.ModelForm):
    class Meta:
        model = BugReport
        fields = (
            "kind",
            "severity",
            "title",
            "description",
            "contact_email",
            "screenshot",
            "viewport_width",
            "viewport_height",
            "screen_width",
            "screen_height",
            "device_pixel_ratio",
            "browser_timezone",
        )
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": _INPUT,
                    "placeholder": "Short summary",
                    "maxlength": 200,
                    "required": True,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": _INPUT,
                    "rows": 6,
                    "placeholder": "What happened? What did you expect? Steps to reproduce.",
                    "required": True,
                }
            ),
            "contact_email": forms.EmailInput(
                attrs={
                    "class": _INPUT,
                    "placeholder": "Optional — if you want a reply",
                }
            ),
            "kind": forms.Select(attrs={"class": _SELECT}),
            "severity": forms.Select(attrs={"class": _SELECT}),
            "screenshot": forms.ClearableFileInput(
                attrs={
                    "class": "hidden",
                    "accept": "image/*",
                    "x-ref": "input",
                    "@change": "setName($event.target)",
                }
            ),
            "viewport_width": forms.HiddenInput(),
            "viewport_height": forms.HiddenInput(),
            "screen_width": forms.HiddenInput(),
            "screen_height": forms.HiddenInput(),
            "device_pixel_ratio": forms.HiddenInput(),
            "browser_timezone": forms.HiddenInput(),
        }
