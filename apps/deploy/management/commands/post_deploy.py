"""Run the after-the-release work that has not run yet.

Called by the deploy once the new code is live and the services have been
restarted, so a step that queues Celery work queues it onto workers running the
same release. Safe to run by hand at any time: a step that is done is skipped.
"""

from django.core.management.base import BaseCommand, CommandError

from webapptemplate.apps.deploy.models import PostDeployStep
from webapptemplate.apps.deploy.runner import discover_steps, fake_step, run_step


class Command(BaseCommand):
    help = "Run post-deploy steps that have not completed yet."

    def add_arguments(self, parser):
        parser.add_argument(
            "--list",
            action="store_true",
            dest="list_steps",
            help="Show every known step and its recorded status; run nothing.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would run; run nothing.",
        )
        parser.add_argument(
            "--only",
            help="Run just this step id.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Run steps that already completed.",
        )
        parser.add_argument(
            "--fake",
            action="store_true",
            help="Record steps as done without running them.",
        )

    def handle(self, *args, **options):
        steps = discover_steps()
        if options["only"]:
            steps = [step for step in steps if step.step_id == options["only"]]
            if not steps:
                raise CommandError(f"No post-deploy step named {options['only']!r}.")

        rows = {
            row.step_id: row
            for row in PostDeployStep.objects.filter(
                step_id__in=[step.step_id for step in steps]
            )
        }

        if options["list_steps"]:
            for step in steps:
                row = rows.get(step.step_id)
                status = row.status if row else "not run"
                self.stdout.write(f"{step.step_id}  {status}  ({step.command_name})")
            if not steps:
                self.stdout.write("No post-deploy steps are registered.")
            return

        if options["fake"]:
            for step in steps:
                fake_step(step)
                self.stdout.write(f"{step.step_id} marked done (--fake)")
            return

        ran = 0
        failed = []
        for step in steps:
            row = rows.get(step.step_id)
            if row is not None and row.status == PostDeployStep.STATUS_RUNNING:
                self.stdout.write(f"{step.step_id} is already running elsewhere; skipping")
                continue
            if row is not None and row.is_settled and not options["force"]:
                continue
            if options["dry_run"]:
                self.stdout.write(f"would run {step.step_id} ({step.command_name})")
                ran += 1
                continue

            self.stdout.write(f"running {step.step_id} ({step.command_name})…")
            result = run_step(step, force=options["force"])
            if result is None:
                self.stdout.write(f"{step.step_id} was claimed elsewhere; skipping")
                continue
            ran += 1
            if result.output:
                self.stdout.write(result.output.rstrip())
            if result.status == PostDeployStep.STATUS_FAILED:
                failed.append(step.step_id)
                self.stderr.write(f"{step.step_id} FAILED\n{result.error}")
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"{step.step_id} done in {result.duration_ms} ms")
                )

        verb = "would run" if options["dry_run"] else "ran"
        self.stdout.write(f"{verb} {ran} post-deploy step(s).")
        if failed:
            raise CommandError(
                "post-deploy steps failed: " + ", ".join(failed)
            )
