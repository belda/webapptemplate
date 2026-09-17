import tempfile
from pathlib import Path

from django.test import SimpleTestCase, override_settings

from webapptemplate.apps.workspaces.templatetags.asset_tags import asset


class AssetTagTest(SimpleTestCase):
    """`{% asset %}` busts the browser cache in dev, and is a no-op in production."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        (Path(self._tmp.name) / "probe.css").write_text("/* probe */")
        override = override_settings(STATICFILES_DIRS=[self._tmp.name])
        override.enable()
        self.addCleanup(override.disable)

    @override_settings(DEBUG=True)
    def test_debug_appends_mtime_cache_buster(self):
        url = asset("probe.css")
        base, _, query = url.partition("?")
        self.assertTrue(base.endswith("probe.css"))
        self.assertTrue(query.startswith("v="))
        self.assertTrue(query[2:].isdigit())

    @override_settings(DEBUG=False)
    def test_production_returns_plain_static_url(self):
        self.assertNotIn("?v=", asset("probe.css"))

    @override_settings(DEBUG=True)
    def test_missing_file_falls_back_to_plain_url(self):
        self.assertNotIn("?v=", asset("does-not-exist.css"))
