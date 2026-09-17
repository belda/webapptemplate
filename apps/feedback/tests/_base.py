import shutil
import tempfile

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from webapptemplate.apps.workspaces.models import Membership, Workspace

User = get_user_model()


@override_settings(REQUIRE_EMAIL_VERIFICATION=False)
class WorkspaceTestCase(TestCase):
    """One workspace with two members, plus a throwaway MEDIA_ROOT.

    The media redirect matters here: reports carry a screenshot and updates
    carry an attachment, so without it every run leaves files in the real
    media/ tree.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_tmp = tempfile.mkdtemp(prefix="feedback-test-media-")
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_tmp)
        cls._media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._media_override.disable()
        shutil.rmtree(cls._media_tmp, ignore_errors=True)
        super().tearDownClass()

    @classmethod
    def setUpTestData(cls):
        cls.manager = cls._make_user("manager@example.com")
        cls.workspace = Workspace.objects.create(name="Feedback WS", owner=cls.manager)
        Membership.objects.create(
            user=cls.manager, workspace=cls.workspace, role=Membership.ROLE_OWNER
        )
        cls.artist = cls._make_user("artist@example.com")
        Membership.objects.create(
            user=cls.artist, workspace=cls.workspace, role=Membership.ROLE_MEMBER
        )

    @staticmethod
    def _make_user(email):
        user = User.objects.create_user(
            email=email, username=email.split("@")[0], password="testpass123"
        )
        EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)
        return user
