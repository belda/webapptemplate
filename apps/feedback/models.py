from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.db import models
from django.db import transaction

from .links import absolute_url
from webapptemplate.apps.workspaces.models import Workspace


def _app_name() -> str:
    return getattr(settings, "APP_NAME", "the app")


class BugReport(models.Model):
    KIND_BUG = "bug"
    KIND_WISH = "wish"
    KIND_QUESTION = "question"
    KIND_OTHER = "other"
    KIND_CHOICES = [
        (KIND_BUG, "Bug — something is broken"),
        (KIND_WISH, "Wish — feature request"),
        (KIND_QUESTION, "Question"),
        (KIND_OTHER, "Other"),
    ]

    SEVERITY_LOW = "low"
    SEVERITY_MEDIUM = "medium"
    SEVERITY_HIGH = "high"
    SEVERITY_BLOCKER = "blocker"
    SEVERITY_CHOICES = [
        (SEVERITY_LOW, "Low — minor annoyance"),
        (SEVERITY_MEDIUM, "Medium — workaround exists"),
        (SEVERITY_HIGH, "High — major impact"),
        (SEVERITY_BLOCKER, "Blocker — cannot continue"),
    ]

    STATUS_NEW = "new"
    STATUS_TRIAGED = "triaged"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_RESOLVED = "resolved"
    STATUS_WONT_FIX = "wont_fix"
    STATUS_DUPLICATE = "duplicate"
    STATUS_CHOICES = [
        (STATUS_NEW, "New"),
        (STATUS_TRIAGED, "Triaged"),
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_RESOLVED, "Resolved"),
        (STATUS_WONT_FIX, "Won't fix"),
        (STATUS_DUPLICATE, "Duplicate"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bug_reports",
    )
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bug_reports",
    )

    kind = models.CharField(max_length=16, choices=KIND_CHOICES, default=KIND_BUG)
    severity = models.CharField(
        max_length=16, choices=SEVERITY_CHOICES, default=SEVERITY_MEDIUM
    )
    title = models.CharField(max_length=200)
    description = models.TextField(
        help_text="What happened, what you expected, and how to reproduce."
    )
    contact_email = models.EmailField(blank=True)

    page_url = models.URLField(max_length=500, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    viewport_width = models.PositiveIntegerField(null=True, blank=True)
    viewport_height = models.PositiveIntegerField(null=True, blank=True)
    screen_width = models.PositiveIntegerField(null=True, blank=True)
    screen_height = models.PositiveIntegerField(null=True, blank=True)
    device_pixel_ratio = models.FloatField(null=True, blank=True)
    browser_timezone = models.CharField(max_length=100, blank=True)

    screenshot = models.ImageField(upload_to="feedback/screenshots/%Y/%m/", blank=True, null=True)

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_NEW)
    admin_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["kind", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"[{self.get_kind_display()}] {self.title}"

    STATUS_FLOW = (STATUS_NEW, STATUS_TRIAGED, STATUS_IN_PROGRESS, STATUS_RESOLVED)

    @property
    def is_open(self) -> bool:
        return self.status in {
            self.STATUS_NEW,
            self.STATUS_TRIAGED,
            self.STATUS_IN_PROGRESS,
        }

    @property
    def is_resolved(self) -> bool:
        return self.status == self.STATUS_RESOLVED

    @property
    def on_tracker(self) -> bool:
        """Whether this report moves along the New→Resolved progress track
        (vs. the terminal Won't fix / Duplicate outcomes)."""
        return self.status in self.STATUS_FLOW

    @property
    def tracker_steps(self):
        keys = list(self.STATUS_FLOW)
        current_index = keys.index(self.status) if self.status in keys else -1
        labels = ["New", "Triaged", "In progress", "Resolved"]
        return [
            {
                "label": label,
                "done": current_index >= 0 and index <= current_index,
                "current": index == current_index,
            }
            for index, label in enumerate(labels)
        ]

    def save(self, *args, **kwargs):
        previous_status = None
        update_fields = kwargs.get("update_fields")
        status_can_change = update_fields is None or "status" in update_fields
        if self.pk and status_can_change:
            previous_status = (
                type(self).objects.filter(pk=self.pk)
                .values_list("status", flat=True)
                .first()
            )

        super().save(*args, **kwargs)

        skip_email = getattr(self, "_skip_status_email", False)
        if (
            not skip_email
            and previous_status
            and previous_status != self.status
            and self.contact_email
        ):
            transaction.on_commit(
                lambda: self._send_status_change_email(previous_status)
            )

    def _send_status_change_email(self, previous_status):
        previous_display = dict(self.STATUS_CHOICES).get(
            previous_status, previous_status
        )
        current_display = self.get_status_display()
        subject = f"Bug report status changed: {self.title}"
        lines = [
            (
                f'Your report "{self.title}" changed from '
                f"{previous_display} to {current_display}."
            ),
            "",
            "Report details:",
            f"- Type: {self.get_kind_display()}",
            f"- Severity: {self.get_severity_display()}",
        ]
        if self.page_url:
            lines.append(f"- Page: {self.page_url}")
        lines.extend(
            [
                "",
                f"Thanks for helping improve {_app_name()}.",
            ]
        )
        send_mail(
            subject,
            "\n".join(lines),
            settings.DEFAULT_FROM_EMAIL,
            [self.contact_email],
            fail_silently=False,
        )


class BugReportUpdate(models.Model):
    """One operator action on a report: an optional status change plus an
    optional message (and attachment) sent to the reporter. Rows are an
    append-only history — the reporter and the admin both read them in order."""

    INLINE_ATTACH_MAX_BYTES = 5 * 1024 * 1024

    report = models.ForeignKey(
        BugReport,
        on_delete=models.CASCADE,
        related_name="updates",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bug_report_updates",
    )

    old_status = models.CharField(
        max_length=16, choices=BugReport.STATUS_CHOICES, blank=True
    )
    new_status = models.CharField(
        max_length=16,
        choices=BugReport.STATUS_CHOICES,
        blank=True,
        help_text="Leave blank to send a message without changing the status.",
    )
    message = models.TextField(
        blank=True,
        help_text="Sent to the reporter and shown on their reports page.",
    )
    attachment = models.FileField(
        upload_to="feedback/attachments/%Y/%m/", blank=True, null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        if self.new_status:
            return f"{self.old_status or '—'} → {self.new_status}"
        return "message"

    @property
    def changed_status(self) -> bool:
        return bool(self.new_status) and self.new_status != self.old_status

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if is_new and not self.old_status:
            self.old_status = self.report.status

        apply_transition = is_new and self.changed_status
        if apply_transition:
            self.report.status = self.new_status
            self.report._skip_status_email = True
            self.report.save(update_fields=["status"])

        super().save(*args, **kwargs)

        if is_new and self.report.contact_email and (self.message or apply_transition):
            transaction.on_commit(self._send_email)

    def _send_email(self):
        report = self.report
        if self.changed_status:
            old_display = dict(BugReport.STATUS_CHOICES).get(
                self.old_status, self.old_status
            )
            new_display = dict(BugReport.STATUS_CHOICES).get(
                self.new_status, self.new_status
            )
            subject = f"Update on your report: {report.title}"
            intro = (
                f'Your report "{report.title}" moved from '
                f"{old_display} to {new_display}."
            )
        else:
            subject = f"Message about your report: {report.title}"
            intro = f'A note about your report "{report.title}":'

        lines = [intro]
        if self.message:
            lines.extend(["", self.message])

        attach_inline = self.attachment and self.attachment.size <= self.INLINE_ATTACH_MAX_BYTES
        if self.attachment and not attach_inline:
            link = absolute_url(self.attachment.url)
            lines.extend(["", f"Attachment: {link}"])

        if report.page_url:
            lines.extend(["", f"Page: {report.page_url}"])
        lines.extend(["", f"Thanks for helping improve {_app_name()}."])

        email = EmailMessage(
            subject,
            "\n".join(lines),
            settings.DEFAULT_FROM_EMAIL,
            [report.contact_email],
        )
        if attach_inline:
            self.attachment.open("rb")
            try:
                email.attach(
                    self.attachment.name.rsplit("/", 1)[-1],
                    self.attachment.read(),
                )
            finally:
                self.attachment.close()
        email.send(fail_silently=False)
