"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import tempfile
from pathlib import Path

from django.test import RequestFactory, SimpleTestCase, override_settings

from ng_seed.views import seed_angular


class SeedAngularStaticViewTests(SimpleTestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.static_root = Path(tmp.name) / "static"
        browser = self.static_root / "ng-app" / "browser"
        browser.mkdir(parents=True)
        (browser / "index.html").write_text("<html>index</html>")
        (browser / "main.js").write_text("console.log('main')")
        (browser / "assets.v1").mkdir()
        (Path(tmp.name) / "secret.txt").write_text("TOP SECRET")

        override = override_settings(STATIC_ROOT=str(self.static_root))
        override.enable()
        self.addCleanup(override.disable)

    def get(self, path):
        response = seed_angular(RequestFactory().get(path))
        return response, b"".join(response) if response.streaming else response.content

    def test_serves_asset(self):
        response, body = self.get("/ng-app/main.js")
        assert response.status_code == 200
        assert body == b"console.log('main')"

    def test_falls_back_to_index(self):
        response, body = self.get("/ng-app/some/route")
        assert response.status_code == 200
        assert body == b"<html>index</html>"

    def test_traversal_does_not_escape_static_root(self):
        for path in (
            "/ng-app/../../secret.txt",
            "/ng-app/browser/../../../secret.txt",
            "/ng-app/%2e%2e/%2e%2e/secret.txt",
            f"/ng-app/{self.static_root.parent}/secret.txt",
            "/ng-app//etc/hosts",
        ):
            response, body = self.get(path)
            assert response.status_code == 200, path
            assert b"SECRET" not in body, path
            assert body == b"<html>index</html>", path

    def test_directory_with_dot_falls_back_to_index(self):
        response, body = self.get("/ng-app/assets.v1")
        assert response.status_code == 200
        assert body == b"<html>index</html>"
