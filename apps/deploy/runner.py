"""Discovery and execution of post-deploy steps.

Discovery mirrors migrations: every management command in a first-party app that
subclasses :class:`~webapptemplate.apps.deploy.base.PostDeployCommand` is a step,
sorted by its id. Only our own apps are imported to be asked — a third-party
command is never loaded just to discover it is not a step.
"""

import io
import traceback
from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command, get_commands, load_command_class
from django.db import transaction
from django.utils import timezone

from .base import PostDeployCommand
from .models import PostDeployStep

OUTPUT_MAX_CHARS = 20000

# Which app labels are searched for steps. Both prefixes ship by default: the
# framework apps live under `webapptemplate.apps.`, and a scaffolded project's
# own apps under `apps.`. Override POST_DEPLOY_APP_PREFIXES if you nest yours
# somewhere else.
DEFAULT_APP_PREFIXES = ("apps.", "webapptemplate.apps.")


@dataclass(frozen=True)
class DiscoveredStep:
    step_id: str
    command_name: str
    app_name: str
    help_text: str


def discover_steps() -> list[DiscoveredStep]:
    prefixes = tuple(
        getattr(settings, "POST_DEPLOY_APP_PREFIXES", DEFAULT_APP_PREFIXES)
    )
    steps: dict[str, DiscoveredStep] = {}
    for command_name, app_name in get_commands().items():
        if not isinstance(app_name, str) or not app_name.startswith(prefixes):
            continue
        command = load_command_class(app_name, command_name)
        if not isinstance(command, PostDeployCommand):
            continue
        step_id = (command.post_deploy_id or "").strip()
        if not step_id:
            raise ImproperlyConfigured(
                f"{app_name}.{command_name} is a PostDeployCommand without a "
                "post_deploy_id."
            )
        existing = steps.get(step_id)
        if existing is not None:
            raise ImproperlyConfigured(
                f"Post-deploy id {step_id!r} is claimed by both "
                f"{existing.command_name} and {command_name}."
            )
        steps[step_id] = DiscoveredStep(
            step_id=step_id,
            command_name=command_name,
            app_name=app_name,
            help_text=(command.help or "").strip(),
        )
    return sorted(steps.values(), key=lambda step: step.step_id)


def _claim(step: DiscoveredStep, *, force: bool) -> PostDeployStep | None:
    """Move the step's row to ``running``, or return ``None`` if it must not run.

    The select-for-update is what stops two deploys landing on one step: the
    second one reads the row the first already flipped to ``running``.
    """
    with transaction.atomic():
        row, _ = PostDeployStep.objects.get_or_create(
            step_id=step.step_id,
            defaults={"command_name": step.command_name},
        )
        row = PostDeployStep.objects.select_for_update().get(pk=row.pk)
        if row.status == PostDeployStep.STATUS_RUNNING:
            return None
        if row.is_settled and not force:
            return None
        row.command_name = step.command_name
        row.status = PostDeployStep.STATUS_RUNNING
        row.attempts += 1
        row.started_at = timezone.now()
        row.finished_at = None
        row.error = ""
        row.output = ""
        row.save(
            update_fields=[
                "command_name",
                "status",
                "attempts",
                "started_at",
                "finished_at",
                "error",
                "output",
                "updated_at",
            ]
        )
        return row


def _settle(row: PostDeployStep, status: str, output: str, error: str = "") -> None:
    row.status = status
    row.finished_at = timezone.now()
    if row.started_at:
        elapsed = (row.finished_at - row.started_at).total_seconds()
        row.duration_ms = max(0, int(elapsed * 1000))
    row.output = output[-OUTPUT_MAX_CHARS:]
    row.error = error[-OUTPUT_MAX_CHARS:]
    row.save(
        update_fields=[
            "status",
            "finished_at",
            "duration_ms",
            "output",
            "error",
            "updated_at",
        ]
    )


def run_step(step: DiscoveredStep, *, force: bool = False) -> PostDeployStep | None:
    """Run one step and record the attempt. ``None`` means it was not eligible."""
    row = _claim(step, force=force)
    if row is None:
        return None
    buffer = io.StringIO()
    try:
        call_command(step.command_name, stdout=buffer, stderr=buffer)
    except Exception:
        _settle(
            row,
            PostDeployStep.STATUS_FAILED,
            buffer.getvalue(),
            traceback.format_exc(),
        )
    else:
        _settle(row, PostDeployStep.STATUS_DONE, buffer.getvalue())
    return row


def fake_step(step: DiscoveredStep) -> PostDeployStep:
    """Record a step as done without running it."""
    row, _ = PostDeployStep.objects.get_or_create(
        step_id=step.step_id,
        defaults={"command_name": step.command_name},
    )
    row.command_name = step.command_name
    row.status = PostDeployStep.STATUS_DONE
    row.finished_at = timezone.now()
    row.output = "Marked done with --fake; the step did not run."
    row.error = ""
    row.save(
        update_fields=[
            "command_name",
            "status",
            "finished_at",
            "output",
            "error",
            "updated_at",
        ]
    )
    return row


def pending_steps(steps: list[DiscoveredStep]) -> list[DiscoveredStep]:
    settled = set(
        PostDeployStep.objects.filter(
            step_id__in=[step.step_id for step in steps],
            status__in=PostDeployStep.SETTLED_STATUSES,
        ).values_list("step_id", flat=True)
    )
    return [step for step in steps if step.step_id not in settled]
