from django.contrib import admin

from .models import PostDeployStep


@admin.register(PostDeployStep)
class PostDeployStepAdmin(admin.ModelAdmin):
    list_display = (
        "step_id",
        "status",
        "attempts",
        "duration_ms",
        "finished_at",
    )
    list_filter = ("status",)
    search_fields = ("step_id", "command_name")
    ordering = ("step_id",)
    # Status is editable on purpose: a backfill that failed against real data is
    # re-armed by setting it back to pending, and one that was handled by hand is
    # closed by setting it to done.
    fields = (
        "step_id",
        "command_name",
        "status",
        "attempts",
        "started_at",
        "finished_at",
        "duration_ms",
        "output",
        "error",
    )
    readonly_fields = (
        "step_id",
        "command_name",
        "attempts",
        "started_at",
        "finished_at",
        "duration_ms",
        "output",
        "error",
    )

    def has_add_permission(self, request):
        # Steps come from discovery; an invented row would never match a command.
        return False
