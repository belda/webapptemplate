from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.accounts.forms import ProfileForm

User = get_user_model()


class ProfileFormFieldsTest(TestCase):
    """ProfileForm must not expose the email field (security: changes go through allauth)."""

    def test_email_field_not_present(self):
        form = ProfileForm()
        self.assertNotIn("email", form.fields)

    def test_only_name_fields_exposed(self):
        form = ProfileForm()
        self.assertEqual(set(form.fields.keys()), {"first_name", "last_name"})

    def test_form_saves_name_fields(self):
        user = User.objects.create_user(
            email="alice@example.com",
            username="alice",
            password="testpass123",
        )
        user.refresh_from_db()
        form = ProfileForm({"first_name": "Alice", "last_name": "Smith"}, instance=user)
        self.assertTrue(form.is_valid())
        saved = form.save()
        self.assertEqual(saved.first_name, "Alice")
        self.assertEqual(saved.last_name, "Smith")

    def test_email_cannot_be_changed_via_form(self):
        """Submitting an email value in POST data must not update the email."""
        user = User.objects.create_user(
            email="original@example.com",
            username="original",
            password="testpass123",
        )
        user.refresh_from_db()
        original_email = user.email
        # Attempt to sneak an email change via POST data
        form = ProfileForm(
            {"first_name": "Bob", "last_name": "Jones", "email": "hacker@evil.com"},
            instance=user,
        )
        self.assertTrue(form.is_valid())
        saved = form.save()
        saved.refresh_from_db()
        self.assertEqual(saved.email, original_email)
