from django.db import models


class PostDeployStep(models.Model):
    """One named unit of after-the-deploy work and what happened when it ran.

    The row is the memory: a step that reached ``done`` is never run again, the
    way an applied migration is never re-applied. A step that failed did not
    succeed, so it stays unsettled and the next deploy retries it.
    """

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_DONE = "done"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_DONE, "Done"),
        (STATUS_FAILED, "Failed"),
        (STATUS_SKIPPED, "Skipped"),
    ]
    SETTLED_STATUSES = (STATUS_DONE, STATUS_SKIPPED)

    step_id = models.CharField(max_length=200, unique=True)
    command_name = models.CharField(max_length=200, blank=True, default="")
    status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    attempts = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    output = models.TextField(blank=True, default="")
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["step_id"]

    def __str__(self):
        return f"{self.step_id} [{self.status}]"

    @property
    def is_settled(self) -> bool:
        return self.status in self.SETTLED_STATUSES
