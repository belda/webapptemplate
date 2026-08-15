from io import StringIO
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import TestCase

from webapptemplate.apps.deploy.models import PostDeployStep
from webapptemplate.apps.deploy.runner import discover_steps, pending_steps

# Absolute, not relative: apps/ is also reachable as webapptemplate/apps/ (a
# symlink), so a relative import here would bind a *different* module object
# than the one load_command_class imports via FAKE_APP below — and the `runs`
# list the assertions read would never be the one the command appended to.
from webapptemplate.apps.deploy.tests.fakeapp.management.commands import (  # noqa: E402
    step_fail,
    step_ok,
)

FAKE_APP = "webapptemplate.apps.deploy.tests.fakeapp"
FAKE_COMMANDS = {
    "post_deploy": "webapptemplate.apps.deploy",
    "step_ok": FAKE_APP,
    "step_fail": FAKE_APP,
    "step_plain": FAKE_APP,
    "runserver": "django.core",
}

OK_ID = "20990101_step_ok"
FAIL_ID = "20990102_step_fail"


def run(*args):
    out, err = StringIO(), StringIO()
    call_command("post_deploy", *args, stdout=out, stderr=err)
    return out.getvalue() + err.getvalue()


class PostDeployStepTests(TestCase):
    def setUp(self):
        # Discovery reads its own import; call_command reads Django's.
        for target in ("webapptemplate.apps.deploy.runner.get_commands", "django.core.management.get_commands"):
            patcher = patch(target, return_value=FAKE_COMMANDS)
            patcher.start()
            self.addCleanup(patcher.stop)
        step_ok.runs.clear()
        step_fail.runs.clear()

    def test_discovery_finds_only_declared_steps_in_id_order(self):
        found = discover_steps()

        self.assertEqual([step.step_id for step in found], [OK_ID, FAIL_ID])
        self.assertEqual(found[0].command_name, "step_ok")

    def test_a_step_runs_once_and_is_remembered(self):
        run("--only", OK_ID)

        row = PostDeployStep.objects.get(step_id=OK_ID)
        self.assertEqual(row.status, PostDeployStep.STATUS_DONE)
        self.assertEqual(row.attempts, 1)
        self.assertIn("ok step said something", row.output)
        self.assertIsNotNone(row.finished_at)
        self.assertEqual(step_ok.runs, [OK_ID])

    def test_a_second_run_does_nothing(self):
        run("--only", OK_ID)
        output = run("--only", OK_ID)

        self.assertEqual(step_ok.runs, [OK_ID])
        self.assertEqual(PostDeployStep.objects.get(step_id=OK_ID).attempts, 1)
        self.assertIn("ran 0 post-deploy step(s)", output)

    def test_force_runs_a_completed_step_again(self):
        run("--only", OK_ID)
        run("--only", OK_ID, "--force")

        self.assertEqual(step_ok.runs, [OK_ID, OK_ID])
        self.assertEqual(PostDeployStep.objects.get(step_id=OK_ID).attempts, 2)

    def test_a_failing_step_is_recorded_and_retried_next_run(self):
        with self.assertRaises(CommandError):
            run("--only", FAIL_ID)

        row = PostDeployStep.objects.get(step_id=FAIL_ID)
        self.assertEqual(row.status, PostDeployStep.STATUS_FAILED)
        self.assertIn("the backfill hit real data", row.error)
        self.assertIn("got as far as this", row.output)

        with self.assertRaises(CommandError):
            run("--only", FAIL_ID)

        row.refresh_from_db()
        self.assertEqual(row.attempts, 2)
        self.assertEqual(step_fail.runs, [FAIL_ID, FAIL_ID])

    def test_one_failure_does_not_stop_the_other_steps(self):
        with self.assertRaises(CommandError):
            run()

        self.assertEqual(
            PostDeployStep.objects.get(step_id=OK_ID).status,
            PostDeployStep.STATUS_DONE,
        )
        self.assertEqual(
            PostDeployStep.objects.get(step_id=FAIL_ID).status,
            PostDeployStep.STATUS_FAILED,
        )

    def test_a_step_running_elsewhere_is_left_alone(self):
        PostDeployStep.objects.create(
            step_id=OK_ID,
            command_name="step_ok",
            status=PostDeployStep.STATUS_RUNNING,
        )

        output = run("--only", OK_ID)

        self.assertEqual(step_ok.runs, [])
        self.assertIn("already running elsewhere", output)

    def test_a_step_marked_skipped_by_hand_stays_skipped(self):
        PostDeployStep.objects.create(
            step_id=OK_ID,
            command_name="step_ok",
            status=PostDeployStep.STATUS_SKIPPED,
        )

        run("--only", OK_ID)

        self.assertEqual(step_ok.runs, [])

    def test_fake_settles_a_step_without_running_it(self):
        run("--only", OK_ID, "--fake")

        row = PostDeployStep.objects.get(step_id=OK_ID)
        self.assertEqual(row.status, PostDeployStep.STATUS_DONE)
        self.assertEqual(step_ok.runs, [])
        self.assertEqual(pending_steps(discover_steps()), discover_steps()[1:])

    def test_dry_run_records_nothing(self):
        output = run("--dry-run")

        self.assertIn(f"would run {OK_ID}", output)
        self.assertEqual(PostDeployStep.objects.count(), 0)
        self.assertEqual(step_ok.runs, [])

    def test_list_shows_recorded_status(self):
        run("--only", OK_ID)

        output = run("--list")

        self.assertIn(f"{OK_ID}  done", output)
        self.assertIn(f"{FAIL_ID}  not run", output)
        self.assertEqual(step_ok.runs, [OK_ID])

    def test_an_unknown_step_id_is_an_error(self):
        with self.assertRaises(CommandError):
            run("--only", "20990103_nope")
