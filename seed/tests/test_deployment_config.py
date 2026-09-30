import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from config.settings.common import deployment_image_url
from seed.analysis_pipelines.pipeline import AnalysisPipeline
from seed.decorators import get_bb_salesforce_config
from seed.models import Analysis
from seed.utils.salesforce import test_connection, update_salesforce_property


class DeploymentConfigTests(SimpleTestCase):
    @override_settings(SEED_BRAND_LOGO_URL="", SEED_LOGIN_HEADING="", SEED_LOGIN_TEXT="")
    def test_legacy_login_keeps_split_layout_by_default(self):
        login = render_to_string("two_factor/_base_focus.html", request=RequestFactory().get("/account/login/"))

        self.assertIn('<div class="section_marketing">', login)
        self.assertIn('Log in to SEED Platform', login)
        self.assertIn('landing-bg.webp', login)
        self.assertNotIn('<div class="section_forms deployment-branded">', login)

    @override_settings(SEED_BRAND_LOGO_URL="/branding/client-logo.svg", SEED_LOGIN_HEADING="Client portal", SEED_HOME_HERO_IMAGE_URL="")
    def test_legacy_login_places_custom_logo_above_form(self):
        login = render_to_string("two_factor/_base_focus.html", request=RequestFactory().get("/account/login/"))

        self.assertIn('<div class="section_forms deployment-branded">', login)
        self.assertIn('src="/branding/client-logo.svg"', login)
        self.assertIn('Client portal', login)
        self.assertIn('background: #f3f4f6;', login)
        self.assertIn('background: white;', login)
        self.assertNotIn('landing-bg.webp', login)
        self.assertNotIn('Log in to SEED Platform', login)

    @override_settings(SEED_BRAND_LOGO_URL="/branding/client-logo.svg", SEED_HOME_HERO_IMAGE_URL="/branding/hero.webp")
    def test_custom_hero_can_replace_legacy_login_background(self):
        login = render_to_string("two_factor/_base_focus.html", request=RequestFactory().get("/account/login/"))

        self.assertIn("background: #f3f4f6 url('/branding/hero.webp')", login)
        self.assertNotIn('landing-bg.webp', login)

    def test_external_branding_image_is_rejected(self):
        with patch.dict(os.environ, SEED_BRAND_LOGO_URL="https://images.example.com/logo.svg"), pytest.raises(
            ValueError, match="must be a path under /branding/"
        ):
            deployment_image_url("SEED_BRAND_LOGO_URL")

    @override_settings(
        SEED_HOME_CONTENT_MODE="default",
        SEED_HIDDEN_NAVIGATION=[],
        SEED_SALESFORCE_ENABLED=True,
        SEED_BETTER_ENABLED=True,
    )
    def test_unconfigured_site_uses_existing_defaults(self):
        response = self.client.get("/api/config/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["branding"]["home_content_mode"], "default")
        self.assertEqual(response.json()["hidden_navigation"], [])
        self.assertEqual(response.json()["integrations"], {"salesforce": True, "better": True})

    @override_settings(
        SEED_BRAND_LOGO_URL="/branding/client-logo.svg",
        SEED_LOGIN_HEADING="Client portal",
        SEED_HIDDEN_NAVIGATION=["documentation", "api"],
        SEED_SALESFORCE_ENABLED=False,
        SEED_BETTER_ENABLED=False,
    )
    def test_overrides_are_shared_with_legacy_login(self):
        response = self.client.get("/api/config/")
        branding = response.json()["branding"]
        login = render_to_string("landing/_marketing_bullets.html", request=RequestFactory().get("/"))

        self.assertEqual(branding["logo_url"], "/branding/client-logo.svg")
        self.assertEqual(response.json()["hidden_navigation"], ["documentation", "api"])
        self.assertFalse(response.json()["integrations"]["salesforce"])
        self.assertIn("/branding/client-logo.svg", login)
        self.assertIn("Client portal", login)

    @override_settings(SEED_SALESFORCE_ENABLED=False, SEED_BETTER_ENABLED=False)
    def test_disabled_integrations_do_not_start_clients(self):
        with patch("seed.utils.salesforce.SalesforceClient") as client:
            self.assertFalse(test_connection({})[0])
            client.assert_not_called()
        self.assertEqual(update_salesforce_property(1, 1, salesforce_client=object())[0], False)

        pipeline = AnalysisPipeline.factory(SimpleNamespace(service=Analysis.BETTER, id=1))
        self.assertEqual(type(pipeline).__name__, "BETTERPipeline")

    @override_settings(SEED_SALESFORCE_ENABLED=False)
    def test_bb_salesforce_endpoints_are_blocked_when_disabled(self):
        endpoint = get_bb_salesforce_config(lambda *args, **kwargs: self.fail("Salesforce endpoint should not execute"))

        with self.assertRaisesMessage(PermissionDenied, "Salesforce is disabled on this deployment"):
            endpoint(None, None)
