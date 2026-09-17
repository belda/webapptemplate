from django.contrib import admin
from django.utils.html import format_html

from .models import BugReport, BugReportUpdate


class BugReportUpdateInline(admin.TabularInline):
    model = BugReportUpdate
    extra = 1
    fields = ("new_status", "message", "attachment", "author", "created_at")
    readonly_fields = ("author", "created_at")
    ordering = ("created_at",)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields


@admin.register(BugReport)
class BugReportAdmin(admin.ModelAdmin):
    inlines = [BugReportUpdateInline]
    list_display = (
        "created_at",
        "kind",
        "severity",
        "status",
        "title",
        "user",
        "workspace",
        "page_link",
    )
    list_filter = ("status", "kind", "severity", "created_at", "workspace")
    search_fields = ("title", "description", "user__email", "contact_email", "page_url")
    list_editable = ("status",)
    date_hierarchy = "created_at"
    readonly_fields = (
        "user",
        "workspace",
        "page_url",
        "user_agent",
        "ip_address",
        "viewport_size",
        "screen_size",
        "device_pixel_ratio",
        "browser_timezone",
        "created_at",
        "updated_at",
        "screenshot_preview",
    )
    fieldsets = (
        ("Report", {"fields": ("kind", "severity", "title", "description", "contact_email", "screenshot", "screenshot_preview")}),
        ("Triage", {"fields": ("status", "admin_notes")}),
        (
            "Context",
            {
                "fields": (
                    "user",
                    "workspace",
                    "page_url",
                    "user_agent",
                    "ip_address",
                    "viewport_size",
                    "screen_size",
                    "device_pixel_ratio",
                    "browser_timezone",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, BugReportUpdate) and instance._state.adding:
                instance.author = request.user
            instance.save()
        formset.save_m2m()
        for obj in formset.deleted_objects:
            obj.delete()

    @admin.display(description="Page")
    def page_link(self, obj):
        if not obj.page_url:
            return "—"
        return format_html('<a href="{0}" target="_blank">open</a>', obj.page_url)

    @admin.display(description="Viewport")
    def viewport_size(self, obj):
        if not obj.viewport_width or not obj.viewport_height:
            return "—"
        return f"{obj.viewport_width} x {obj.viewport_height}"

    @admin.display(description="Screen")
    def screen_size(self, obj):
        if not obj.screen_width or not obj.screen_height:
            return "—"
        return f"{obj.screen_width} x {obj.screen_height}"

    @admin.display(description="Screenshot preview")
    def screenshot_preview(self, obj):
        if not obj.screenshot:
            return "—"
        return format_html(
            '<a href="{0}" target="_blank"><img src="{0}" style="max-width:480px; max-height:360px; border:1px solid #ccc;" /></a>',
            obj.screenshot.url,
        )
