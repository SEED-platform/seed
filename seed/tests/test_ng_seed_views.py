"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import tempfile
from pathlib import Path

import pytest
from django.http import Http404
from django.test import RequestFactory, SimpleTestCase, override_settings

from ng_seed.views import seed_angular

INDEX = b"<html>index</html>"


class SeedAngularStaticViewTests(SimpleTestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.static_root = self.tmp / "static"
        self.ng_app = self.static_root / "ng-app"
        self.browser = self.ng_app / "browser"
        self.browser.mkdir(parents=True)
        (self.browser / "index.html").write_bytes(INDEX)
        (self.browser / "main.js").write_text("console.log('main')")
        (self.browser / "assets.v1").mkdir()
        (self.ng_app / "prerendered-routes.json").write_text('{"routes": {}}')

        # Files that must never be served: outside STATIC_ROOT, inside STATIC_ROOT but outside ng-app,
        # and in a sibling directory whose name starts with "ng-app"
        (self.tmp / "secret.txt").write_text("TOP SECRET")
        (self.static_root / "other.txt").write_text("STATIC ROOT SECRET")
        (self.static_root / "ng-app-evil").mkdir()
        (self.static_root / "ng-app-evil" / "evil.txt").write_text("SIBLING SECRET")

        override = override_settings(STATIC_ROOT=str(self.static_root))
        override.enable()
        self.addCleanup(override.disable)

    def get(self, path, **extra):
        response = seed_angular(RequestFactory().get(path, **extra))
        # Cleanups run last-in first-out, so the file is closed before the temporary directory is removed
        self.addCleanup(response.close)
        return response, b"".join(response) if response.streaming else response.content

    def assert_index(self, path):
        response, body = self.get(path)
        assert response.status_code == 200
        assert body == INDEX

    def test_serves_asset(self):
        response, body = self.get("/ng-app/main.js")
        assert response.status_code == 200
        assert body == b"console.log('main')"

    def test_serves_file_from_ng_app_root(self):
        response, body = self.get("/ng-app/prerendered-routes.json")
        assert response.status_code == 200
        assert body == b'{"routes": {}}'

    def test_serves_asset_under_script_prefix(self):
        response, body = self.get("/ng-app/main.js", SCRIPT_NAME="/seed")
        assert response.status_code == 200
        assert body == b"console.log('main')"

    def test_falls_back_to_index(self):
        self.assert_index("/ng-app/some/route")

    def test_traversal_does_not_escape_ng_app(self):
        for path in (
            "/ng-app/../../secret.txt",
            "/ng-app/browser/../../../secret.txt",
            "/ng-app/../other.txt",
            "/ng-app/browser/../../other.txt",
            "/ng-app/../ng-app-evil/evil.txt",
        ):
            with self.subTest(path=path):
                self.assert_index(path)

    def test_absolute_paths_fall_back_to_index(self):
        for path in (
            f"/ng-app/{self.tmp}/secret.txt",
            # Rejected even when it would resolve to a file inside ng-app
            f"/ng-app/{self.browser}/main.js",
            # Windows device namespace path, which makes Path.resolve() raise on Windows
            "/ng-app///./GLOBALROOT/Device/Null/x.js",
        ):
            with self.subTest(path=path):
                self.assert_index(path)

    def test_symlink_out_of_root_falls_back_to_index(self):
        try:
            (self.browser / "leak.txt").symlink_to(self.tmp / "secret.txt")
        except OSError as e:
            self.skipTest(f"cannot create symlinks here: {e}")
        self.assert_index("/ng-app/leak.txt")

    def test_unresolvable_path_falls_back_to_index(self):
        # A NUL byte makes Path.resolve() raise ValueError on POSIX
        self.assert_index("/ng-app/x.%00")

    def test_directory_with_dot_falls_back_to_index(self):
        self.assert_index("/ng-app/assets.v1")

    def test_missing_build_raises_404(self):
        (self.browser / "index.html").unlink()
        with pytest.raises(Http404):
            seed_angular(RequestFactory().get("/ng-app/some/route"))
