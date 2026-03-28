import datetime
from django.db import migrations, models
from django.utils import timezone


def set_default_expiry(apps, schema_editor):
    """Back-fill expires_at for existing invitations that have never expired."""
    Invitation = apps.get_model("workspaces", "Invitation")
    default_expiry = timezone.now() + datetime.timedelta(days=7)
    Invitation.objects.filter(accepted_at__isnull=True, expires_at__isnull=True).update(
        expires_at=default_expiry
    )


class Migration(migrations.Migration):

    dependencies = [
        ("workspaces", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="invitation",
            name="expires_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text="Invitation is invalid after this date. Populated automatically on save.",
            ),
        ),
        migrations.RunPython(set_default_expiry, migrations.RunPython.noop),
    ]
