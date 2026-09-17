from unittest import mock

from allauth.account.models import EmailAddress
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from webapptemplate.apps.feedback.models import BugReport, BugReportUpdate
from ._base import WorkspaceTestCase


class BugReportViewTests(WorkspaceTestCase):
    def setUp(self):
        EmailAddress.objects.update_or_create(
            user=self.artist,
            email=self.artist.email,
            defaults={"verified": True, "primary": True},
        )
        self.client.force_login(self.artist)

    def test_get_modal_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("feedback:bug_report_modal"))
        self.assertEqual(response.status_code, 302)

    def test_get_modal_renders(self):
        response = self.client.get(reverse("feedback:bug_report_modal"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "New bug or wish")

    def test_post_creates_report_with_context(self):
        url = reverse("feedback:bug_report_modal")
        response = self.client.post(
            url,
            data={
                "kind": BugReport.KIND_BUG,
                "severity": BugReport.SEVERITY_HIGH,
                "title": "Save button does nothing",
                "description": "Click Save on song page; nothing happens.",
                "contact_email": "",
                "page_url": "https://example.com/production/songs/1/",
                "viewport_width": "390",
                "viewport_height": "844",
                "screen_width": "390",
                "screen_height": "844",
                "device_pixel_ratio": "3",
                "browser_timezone": "Europe/Prague",
            },
            HTTP_USER_AGENT="TestAgent/1.0",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Thanks for the report")

        report = BugReport.objects.get()
        self.assertEqual(report.title, "Save button does nothing")
        self.assertEqual(report.kind, BugReport.KIND_BUG)
        self.assertEqual(report.severity, BugReport.SEVERITY_HIGH)
        self.assertEqual(report.user, self.artist)
        self.assertEqual(report.page_url, "https://example.com/production/songs/1/")
        self.assertEqual(report.user_agent, "TestAgent/1.0")
        self.assertEqual(report.viewport_width, 390)
        self.assertEqual(report.viewport_height, 844)
        self.assertEqual(report.screen_width, 390)
        self.assertEqual(report.screen_height, 844)
        self.assertEqual(report.device_pixel_ratio, 3)
        self.assertEqual(report.browser_timezone, "Europe/Prague")
        self.assertEqual(report.status, BugReport.STATUS_NEW)
        self.assertEqual(report.contact_email, self.artist.email)

    def test_post_invalid_rerenders_form(self):
        response = self.client.post(
            reverse("feedback:bug_report_modal"),
            data={"kind": BugReport.KIND_BUG, "severity": BugReport.SEVERITY_LOW, "title": "", "description": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "New bug or wish")
        self.assertEqual(BugReport.objects.count(), 0)

    def test_status_change_emails_reporter(self):
        report = BugReport.objects.create(
            user=self.artist,
            workspace=self.workspace,
            kind=BugReport.KIND_BUG,
            severity=BugReport.SEVERITY_MEDIUM,
            title="Modal is clipped",
            description="The bug report modal is clipped on mobile.",
            contact_email="reporter@example.com",
            page_url="https://example.com/production/songs/1/",
        )
        self.assertEqual(mail.outbox, [])

        report.status = BugReport.STATUS_IN_PROGRESS
        with self.captureOnCommitCallbacks(execute=True):
            report.save(update_fields=["status"])

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["reporter@example.com"])
        self.assertIn("Bug report status changed", message.subject)
        self.assertIn("New to In progress", message.body)
        self.assertIn("Modal is clipped", message.body)

    def test_status_neutral_save_does_not_email_reporter(self):
        report = BugReport.objects.create(
            user=self.artist,
            workspace=self.workspace,
            kind=BugReport.KIND_BUG,
            severity=BugReport.SEVERITY_MEDIUM,
            title="Modal is clipped",
            description="The bug report modal is clipped on mobile.",
            contact_email="reporter@example.com",
        )

        report.admin_notes = "Needs review."
        with self.captureOnCommitCallbacks(execute=True):
            report.save(update_fields=["admin_notes"])

        self.assertEqual(mail.outbox, [])


class BugReportUpdateTests(WorkspaceTestCase):
    def _make_report(self, **kwargs):
        return BugReport.objects.create(
            user=self.artist,
            workspace=self.workspace,
            kind=BugReport.KIND_BUG,
            severity=BugReport.SEVERITY_MEDIUM,
            title="Modal is clipped",
            description="The modal is clipped on mobile.",
            contact_email=kwargs.pop("contact_email", "reporter@example.com"),
            **kwargs,
        )

    def test_update_applies_status_and_emails_message(self):
        report = self._make_report()
        with self.captureOnCommitCallbacks(execute=True):
            update = BugReportUpdate.objects.create(
                report=report,
                author=self.manager,
                new_status=BugReport.STATUS_WONT_FIX,
                message="This is by design, we won't change it.",
            )

        report.refresh_from_db()
        self.assertEqual(report.status, BugReport.STATUS_WONT_FIX)
        self.assertEqual(update.old_status, BugReport.STATUS_NEW)
        self.assertTrue(update.changed_status)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["reporter@example.com"])
        self.assertIn("Update on your report", message.subject)
        self.assertIn("New to Won't fix", message.body)
        self.assertIn("This is by design", message.body)

    def test_update_does_not_double_email(self):
        report = self._make_report()
        with self.captureOnCommitCallbacks(execute=True):
            BugReportUpdate.objects.create(
                report=report,
                new_status=BugReport.STATUS_IN_PROGRESS,
                message="On it.",
            )
        self.assertEqual(len(mail.outbox), 1)

    def test_message_only_update_keeps_status(self):
        report = self._make_report(status=BugReport.STATUS_TRIAGED)
        with self.captureOnCommitCallbacks(execute=True):
            update = BugReportUpdate.objects.create(
                report=report,
                message="Can you attach a screenshot?",
            )
        report.refresh_from_db()
        self.assertEqual(report.status, BugReport.STATUS_TRIAGED)
        self.assertFalse(update.changed_status)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Message about your report", mail.outbox[0].subject)

    def test_update_carries_attachment_on_email(self):
        report = self._make_report()
        attachment = SimpleUploadedFile(
            "fix.txt", b"here is the patch", content_type="text/plain"
        )
        with self.captureOnCommitCallbacks(execute=True):
            BugReportUpdate.objects.create(
                report=report,
                new_status=BugReport.STATUS_RESOLVED,
                message="Fixed, see attached.",
                attachment=attachment,
            )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(mail.outbox[0].attachments), 1)
        self.assertEqual(mail.outbox[0].attachments[0][0], "fix.txt")

    def test_large_attachment_becomes_link_not_inline(self):
        report = self._make_report()
        attachment = SimpleUploadedFile(
            "clip.mp4", b"x" * 64, content_type="video/mp4"
        )
        with self.settings(SITE_BASE_URL="https://app.example.com"):
            with mock.patch.object(BugReportUpdate, "INLINE_ATTACH_MAX_BYTES", 16):
                with self.captureOnCommitCallbacks(execute=True):
                    BugReportUpdate.objects.create(
                        report=report,
                        new_status=BugReport.STATUS_RESOLVED,
                        message="Here's a screen recording.",
                        attachment=attachment,
                    )
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.attachments, [])
        self.assertIn("Attachment: https://app.example.com", message.body)
        self.assertIn("clip.mp4", message.body)

    def test_update_without_contact_email_sends_nothing(self):
        report = self._make_report(contact_email="")
        with self.captureOnCommitCallbacks(execute=True):
            BugReportUpdate.objects.create(
                report=report,
                new_status=BugReport.STATUS_RESOLVED,
                message="Done.",
            )
        self.assertEqual(mail.outbox, [])

    def test_updates_shown_on_my_reports(self):
        EmailAddress.objects.update_or_create(
            user=self.artist,
            email=self.artist.email,
            defaults={"verified": True, "primary": True},
        )
        self.client.force_login(self.artist)
        report = self._make_report()
        with self.captureOnCommitCallbacks(execute=True):
            BugReportUpdate.objects.create(
                report=report,
                new_status=BugReport.STATUS_WONT_FIX,
                message="Not a priority right now.",
            )
        response = self.client.get(reverse("feedback:my_reports"))
        self.assertContains(response, "Not a priority right now.")
        self.assertContains(response, "Reply from the team")


class BugReportTrackerTests(WorkspaceTestCase):
    def setUp(self):
        EmailAddress.objects.update_or_create(
            user=self.artist,
            email=self.artist.email,
            defaults={"verified": True, "primary": True},
        )
        self.client.force_login(self.artist)

    def _make_report(self, **kwargs):
        return BugReport.objects.create(
            user=kwargs.pop("user", self.artist),
            workspace=self.workspace,
            kind=BugReport.KIND_BUG,
            severity=BugReport.SEVERITY_MEDIUM,
            title=kwargs.pop("title", "Modal is clipped"),
            description="The modal is clipped on mobile.",
            **kwargs,
        )

    def test_tracker_steps_progress(self):
        report = self._make_report(status=BugReport.STATUS_IN_PROGRESS)
        steps = report.tracker_steps
        self.assertEqual([s["label"] for s in steps], ["New", "Triaged", "In progress", "Resolved"])
        self.assertEqual([s["done"] for s in steps], [True, True, True, False])
        self.assertEqual([s["current"] for s in steps], [False, False, True, False])
        self.assertTrue(report.is_open)
        self.assertTrue(report.on_tracker)

    def test_terminal_status_off_tracker(self):
        report = self._make_report(status=BugReport.STATUS_DUPLICATE)
        self.assertFalse(report.on_tracker)
        self.assertFalse(report.is_open)
        self.assertTrue(all(not s["done"] for s in report.tracker_steps))

    def test_resolved_is_complete(self):
        report = self._make_report(status=BugReport.STATUS_RESOLVED)
        self.assertTrue(report.is_resolved)
        self.assertFalse(report.is_open)
        self.assertTrue(all(s["done"] for s in report.tracker_steps))

    def test_my_reports_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("feedback:my_reports"))
        self.assertEqual(response.status_code, 302)

    def test_my_reports_lists_only_own_reports(self):
        mine = self._make_report(title="My own report")
        self._make_report(user=self.manager, title="Someone else's report")

        response = self.client.get(reverse("feedback:my_reports"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My own report")
        self.assertNotContains(response, "Someone else's report")
        self.assertEqual(list(response.context["reports"]), [mine])
        self.assertEqual(response.context["open_count"], 1)

    def test_my_reports_empty_state(self):
        response = self.client.get(reverse("feedback:my_reports"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nothing here yet")

    def test_create_from_listing_reloads_page(self):
        base = {
            "kind": BugReport.KIND_WISH,
            "severity": BugReport.SEVERITY_LOW,
            "title": "A wish",
            "description": "Would be nice to have dark mode everywhere.",
            "contact_email": "",
        }
        listing = self.client.post(
            reverse("feedback:bug_report_modal"),
            data={**base, "page_url": "https://example.com" + reverse("feedback:my_reports")},
        )
        self.assertContains(listing, "window.location.reload()")

        elsewhere = self.client.post(
            reverse("feedback:bug_report_modal"),
            data={**base, "page_url": "https://example.com/production/songs/1/"},
        )
        self.assertNotContains(elsewhere, "window.location.reload()")
