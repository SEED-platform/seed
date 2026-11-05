"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from seed.landing.models import SEEDUser as User


class RobotsTests(TestCase):
    def test_robots(self):
        response = self.client.get(reverse("robots_txt"))
        self.assertEqual(200, response.status_code)


class ApiSchemaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username="schema@demo.com", email="schema@demo.com", password="test_pass")
        self.client.force_login(self.user)

    def test_swagger_ui(self):
        response = self.client.get(reverse("schema-swagger-ui"))
        self.assertEqual(200, response.status_code)
        self.assertContains(response, 'id="swagger-ui"')
        self.assertContains(response, "drf_spectacular_sidecar/swagger-ui-dist/swagger-ui-bundle.js")

    def test_angular_schema_url_returns_json(self):
        # The Angular frontend's API page fetches the schema from this URL and passes it to Swagger UI unchanged
        response = self.client.get(reverse("schema-swagger-ui"), {"format": "openapi"})
        self.assertEqual(200, response.status_code)
        self.assertTrue(response["Content-Type"].startswith("application/json"))
        schema = response.json()
        self.assertTrue(schema["openapi"].startswith("3."))
        self.assertIn("/api/v3/properties/", schema["paths"])
        # Without servers, Swagger UI sends requests to the origin of the page displaying it
        self.assertNotIn("servers", schema)

    def test_schema(self):
        response = self.client.get(reverse("schema"), {"format": "json"})
        self.assertEqual(200, response.status_code)
        self.assertIn("/api/v3/properties/", response.json()["paths"])

    def test_schema_is_valid_openapi_without_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            # raises if the schema is invalid OpenAPI, or if generating it emits any warnings or errors
            # (e.g., unresolvable serializer fields, untyped path parameters, or annotations it cannot use)
            call_command(
                "spectacular", "--validate", "--fail-on-warn", "--format", "openapi-json", "--file", str(Path(tmp) / "schema.json")
            )
