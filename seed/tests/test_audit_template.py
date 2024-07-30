# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
from datetime import datetime
from unittest import mock

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

# from seed.audit_template.audit_template import build_xml
from seed.audit_template.audit_template import AuditTemplate
from seed.landing.models import SEEDUser as User
from seed.test_helpers.fake import FakeCycleFactory, FakePropertyFactory, FakePropertyStateFactory, FakePropertyViewFactory
from seed.utils.organizations import create_organization

# from seed.utils.encrypt import encrypt


class AuditTemplateViewTests(TestCase):
    def setUp(self):
        self.user_details = {
            "username": "test_user@demo.com",
            "password": "test_pass",
        }
        self.user = User.objects.create_superuser(email="test_user@demo.com", **self.user_details)
        self.org, _, _ = create_organization(self.user)
        self.org.at_organization_token = "fake at_api_token"
        self.org.audit_template_user = "fake at user"
        self.org.audit_template_password = "fake at password"
        # 'password' encrypted
        self.org.audit_template_password = "InBhc3N3b3JkIg:xIgRoZurgtGDvmVEUL5Tx1vGbAQe-Iepsct5hiQx29Q"
        self.org.save()

        self.client.login(**self.user_details)

        self.get_submission_url = reverse("api:v3:audit_template-get-submission", args=["1"])

        self.good_authenticate_response = mock.Mock()
        self.good_authenticate_response.status_code = 200
        self.good_authenticate_response.json = mock.Mock(return_value={"token": "fake token"})

        self.bad_authenticate_response = mock.Mock()
        self.bad_authenticate_response.status_code = 400
        self.bad_authenticate_response.content = {"error": "Invalid email, password or organization_token."}

        self.good_get_submission_response = mock.Mock()
        self.good_get_submission_response.status_code = 200
        self.good_get_submission_response.text = "submission response"
        self.good_get_submission_response.content = "submission response"

    @mock.patch("requests.request")
    def test_get_submission_from_audit_template(self, mock_request):
        # -- Act
        mock_request.side_effect = [self.good_authenticate_response, self.good_get_submission_response]
        response = self.client.get(self.get_submission_url, data={"organization_id": self.org.id})

        # -- Assert
        self.assertEqual(200, response.status_code, response.content)
        self.assertEqual(response.content, b"submission response")


class ExportToAuditTemplate(TestCase):
    def setUp(self):
        HOST = settings.AUDIT_TEMPLATE_HOST
        self.API_URL = f"{HOST}/api/v2"
        self.token_url = f"{self.API_URL}/users/authenticate"
        self.upload_url = f"{self.API_URL}/building_sync/upload"

        self.user_details = {
            "username": "test_user@demo.com",
            "password": "test_pass",
        }
        self.user = User.objects.create_superuser(email="test_user@demo.com", **self.user_details)
        self.org, _, _ = create_organization(self.user)
        self.org.at_organization_token = "fake"
        self.org.audit_template_user = "fake@.com"
        self.org.audit_template_password = "InBhc3N3b3JkIg:xIgRoZurgtGDvmVEUL5Tx1vGbAQe-Iepsct5hiQx29Q"
        self.org.property_display_field = "pm_property_id"
        self.org.save()
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)

        self.cycle = self.cycle_factory.get_cycle(start=datetime(2010, 10, 10, tzinfo=timezone.get_current_timezone()))

        self.client.login(**self.user_details)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.view_factory = FakePropertyViewFactory(organization=self.org)
        self.state_factory = FakePropertyStateFactory(organization=self.org)

        self.state1 = self.state_factory.get_property_state(
            property_name="property1",
            address_line_1="111 One St",
            gross_floor_area=1000,
            city="Denver",
            state="CO",
            postal_code="80209",
            year_built=2000,
        )
        self.state2 = self.state_factory.get_property_state(
            property_name="property ny",
            address_line_1="222 Two St",
            gross_floor_area=1000,
            city="New York",
            state="NY",
            postal_code="80209",
            year_built=2000,
        )
        # missing required fields
        self.state3 = self.state_factory.get_property_state(address_line_1=None)
        # existing audit_template_building_id (will be ignored)
        self.state4 = self.state_factory.get_property_state(
            audit_template_building_id="4444",
            property_name="property 4",
            address_line_1="444 Four St",
            gross_floor_area=1000,
            city="Denver",
            state="CO",
            postal_code="80209",
            year_built=2000,
        )

        self.view1 = self.view_factory.get_property_view(cycle=self.cycle, state=self.state1)
        self.view2 = self.view_factory.get_property_view(cycle=self.cycle, state=self.state2)
        self.view3 = self.view_factory.get_property_view(cycle=self.cycle, state=self.state3)
        self.view4 = self.view_factory.get_property_view(cycle=self.cycle, state=self.state4)

    def test_build_xml_from_property(self):
        """
        Properties must be exported to Audit Template as an XML
        """
        at = AuditTemplate(self.org.id)
        response1 = at.build_xml(self.state1, "Demo City Report", self.state1.pm_property_id)
        response2 = at.build_xml(self.state2, "Demo City Report", self.state2.pm_property_id)
        # property missing required fields
        response3 = at.build_xml(self.state3, "Demo City Report", self.state3.pm_property_id)

        self.assertEqual(tuple, type(response1))
        self.assertEqual(tuple, type(response2))
        self.assertEqual(tuple, type(response3))

        exp = "<auc:BuildingSync"
        self.assertEqual(str, type(response1[0]))
        self.assertEqual(exp, response1[0][:17])
        self.assertTrue("111 One St" in response1[0])
        self.assertFalse("222 Two St" in response1[0])

        self.assertEqual(str, type(response2[0]))
        self.assertEqual(exp, response2[0][:17])
        self.assertFalse("111 One St" in response2[0])
        self.assertTrue("222 Two St" in response2[0])

        self.assertEqual([], response1[1])
        self.assertEqual([], response2[1])

        # property missing required fields
        self.assertIsNone(response3[0])
        messages = response3[1]
        exp_error = f"Validation Error. {self.state3.pm_property_id} must have address_line_1, property_name"
        self.assertEqual("error", messages[0])
        self.assertEqual(exp_error, messages[1])

    @mock.patch("requests.request")
    def test_export_to_audit_template(self, mock_request):
        """
        Converts properties to xmls and exports to Audit Template
        """

        at = AuditTemplate(self.org.id)
        token = "fake token"

        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = json.return_value = {
            "rp_buildings": {"BuildingType-1": "https://fake.gov/rp/buildings/1111"},
            "rp_nyc_properties": {},
        }
        mock_request.return_value = mock_response

        # existing property
        response, messages = at.export_to_audit_template(self.state4, token)
        self.assertIsNone(response)
        exp = ["info", f"{self.state4.pm_property_id}: Existing Audit Template Property"]
        self.assertEqual(exp, messages)

        # invalid property
        response, messages = at.export_to_audit_template(self.state3, token)
        self.assertIsNone(response)
        exp = ["error", f"Validation Error. {self.state3.pm_property_id} must have address_line_1, property_name"]
        self.assertEqual(exp, messages)

        # valid property
        response, messages = at.export_to_audit_template(self.state1, token)
        self.assertEqual([], messages)
        exp = {"rp_buildings": {"BuildingType-1": "https://fake.gov/rp/buildings/1111"}, "rp_nyc_properties": {}}
        self.assertEqual(exp, response.json())

    @mock.patch("requests.request")
    def test_batch_export_to_audit_template(self, mock_request):
        """
        Exports multiple properties to Audit Template
        """
        at = AuditTemplate(self.org.id)

        mock_authenticate_response = mock.Mock()
        mock_authenticate_response.status_code = 200
        mock_authenticate_response.json.return_value = {"token": "fake token"}

        mock_export1_response = mock.Mock()
        mock_export1_response.status_code = 200
        mock_export1_response.json.return_value = {
            "rp_buildings": {"BuildingType-1": "https://fake.gov/rp/buildings/1111"},
            "rp_nyc_properties": {},
        }

        mock_export2_response = mock.Mock()
        mock_export2_response.status_code = 200
        mock_export2_response.json.return_value = {
            "rp_buildings": {"BuildingType-1": "https://fake.gov/rp/buildings/2222"},
            "rp_nyc_properties": {},
        }
        mock_request.side_effect = [mock_authenticate_response, mock_export1_response, mock_export2_response]

        # check status of audit_template_building_ids
        self.assertIsNone(self.state1.audit_template_building_id)
        self.assertIsNone(self.state2.audit_template_building_id)
        self.assertIsNone(self.state3.audit_template_building_id)
        self.assertEqual("4444", self.state4.audit_template_building_id)

        results, _ = at.batch_export_to_audit_template([self.view1.id, self.view2.id, self.view3.id, self.view4.id])
        message = results["message"]
        self.assertEqual(["error", "info", "success"], sorted(message.keys()))
        # refresh data
        self.state1.refresh_from_db()
        self.state2.refresh_from_db()
        self.state3.refresh_from_db()
        self.state4.refresh_from_db()

        success = message["success"]
        info = message["info"]
        error = message["error"]

        self.assertEqual(2, success["count"])
        self.assertEqual(1, info["count"])
        self.assertEqual(1, error["count"])

        details = success["details"]
        self.assertEqual(self.view1.id, details[0]["view_id"])
        self.assertEqual("1111", details[0]["at_building_id"])
        self.assertEqual("1111", self.state1.audit_template_building_id)

        self.assertEqual(self.view2.id, details[1]["view_id"])
        self.assertEqual("2222", success["details"][1]["at_building_id"])
        self.assertEqual("2222", self.state2.audit_template_building_id)

        details = error["details"]
        exp = f"Validation Error. {self.state3.pm_property_id} must have address_line_1, property_name"
        self.assertEqual(self.view3.id, details[0]["view_id"])
        self.assertEqual(exp, details[0]["message"])
        self.assertIsNone(self.state3.audit_template_building_id)

        details = info["details"]
        exp = f"{self.state4.pm_property_id}: Existing Audit Template Property"
        self.assertEqual(self.view4.id, details[0]["view_id"])
        self.assertEqual(exp, details[0]["message"])
        self.assertEqual("4444", self.state4.audit_template_building_id)


# For developer use only. Must be run with live submission data.
class AuditTemplateSubmissionImport(TestCase):
    def setUp(self):
        settings.AUDIT_TEMPLATE_HOST = "https://staging.labworks.org"
        self.user_details = {
            "username": "test_user@demo.com",
            "password": "test_pass",
        }
        self.user = User.objects.create_superuser(email="test_user@demo.com", **self.user_details)
        self.org, _, _ = create_organization(self.user)
        # To run test, enter valid audit template credentials
        self.org.at_organization_token = False
        self.org.audit_template_user = False
        self.org.audit_template_password = False  # password must be encrypted: encrypt('password')
        self.skip_test = (
            not self.org.at_organization_token
            or not self.org.audit_template_user
            or not self.org.audit_template_password
            or settings.AUDIT_TEMPLATE_HOST != "https://staging.labworks.org"
        )

        self.org.audit_template_city_id = 36
        self.org.save()
        self.at = AuditTemplate(self.org.id)

        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)

        self.cycle2023 = self.cycle_factory.get_cycle(
            start=datetime(2023, 1, 1, tzinfo=timezone.get_current_timezone()),
            end=datetime(2024, 1, 1, tzinfo=timezone.get_current_timezone()),
        )
        self.cycle2020 = self.cycle_factory.get_cycle(
            start=datetime(2020, 1, 1, tzinfo=timezone.get_current_timezone()),
            end=datetime(2021, 1, 1, tzinfo=timezone.get_current_timezone()),
        )

        self.client.login(**self.user_details)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.view_factory = FakePropertyViewFactory(organization=self.org)
        self.state_factory = FakePropertyStateFactory(organization=self.org)

        self.state1 = self.state_factory.get_property_state(address_line_1="old address 1", custom_id_1="ABC123")
        self.state2 = self.state_factory.get_property_state(address_line_1="old address 2", custom_id_1="ABC123")
        self.state3 = self.state_factory.get_property_state(address_line_1="old address 3", custom_id_1="not_a_match")
        self.state4 = self.state_factory.get_property_state(address_line_1="old address 4")

        self.view1 = self.view_factory.get_property_view(cycle=self.cycle2023, state=self.state1)
        self.view2 = self.view_factory.get_property_view(cycle=self.cycle2020, state=self.state2)
        self.view3 = self.view_factory.get_property_view(cycle=self.cycle2023, state=self.state3)
        self.view4 = self.view_factory.get_property_view(cycle=self.cycle2020, state=self.state4)

    def test_audit_template_submissions(self):
        if self.skip_test:
            self.skipTest("This test is skipped in non-development environments as it is only relevant for developer checks.")

        assert self.view1.state.address_line_1 == "old address 1"
        assert self.view2.state.address_line_1 == "old address 2"
        assert self.view3.state.address_line_1 == "old address 3"
        assert self.view4.state.address_line_1 == "old address 4"

        assert not self.view1.state.audit_template_building_id
        assert not self.view1.state.extra_data

        self.at.batch_get_city_submission_xml()

        for view in [self.view1, self.view2, self.view3, self.view4]:
            view.refresh_from_db()

        # view1's state is the only state that matches the AT response's tax_id (custom_id_1) and cycle dates
        assert (
            self.view1.state.address_line_1 == "ABC Street"
        ), "IMPORTANT: To run this test comment out 'state__updated__lte=updated_at' in view filter (line 475 -ish) in /audit_template/audit_template.py _batch_get_city_submission_xml"
        assert self.view2.state.address_line_1 == "old address 2"
        assert self.view3.state.address_line_1 == "old address 3"
        assert self.view4.state.address_line_1 == "old address 4"

        assert self.view1.state.extra_data
        assert self.view1.state.audit_template_building_id == "1182"

    def test_audit_template_submissions_view(self):
        if self.skip_test:
            self.skipTest("This test is skipped in non-development environments as it is only relevant for developer checks.")

        self.view1.state.address_line_1 = "old address 1"
        self.view1.state.save()

        assert self.view1.state.address_line_1 == "old address 1"
        assert self.view2.state.address_line_1 == "old address 2"
        assert self.view3.state.address_line_1 == "old address 3"
        assert self.view4.state.address_line_1 == "old address 4"

        url = reverse("api:v3:audit_template-batch-get-city-submission-xml") + f"?organization_id={self.org.id}"
        params = {"city_id": self.org.audit_template_city_id}
        self.client.put(url, params, content_type="application/json")

        for view in [self.view1, self.view2, self.view3, self.view4]:
            view.refresh_from_db()
        assert (
            self.view1.state.address_line_1 == "ABC Street"
        ), "IMPORTANT: To run this test comment out 'state__updated__lte=updated_at' from view filter (line 475 -ish) in /audit_template/audit_template.py _batch_get_city_submission_xml"
        assert self.view2.state.address_line_1 == "old address 2"
        assert self.view3.state.address_line_1 == "old address 3"
        assert self.view4.state.address_line_1 == "old address 4"

    def test_audit_template_single_submission(self):
        if self.skip_test:
            self.skipTest("This test is skipped in non-development environments as it is only relevant for developer checks.")

        self.view1.state.address_line_1 = "old address 1"
        self.view1.state.save()

        url = reverse("api:v3:audit_template-get-city-submission-xml") + f"?organization_id={self.org.id}"
        params = {"city_id": self.org.audit_template_city_id, "custom_id_1": self.view1.state.custom_id_1}
        self.client.put(url, params, content_type="application/json")

        self.view1.refresh_from_db()
        assert self.view1.state.address_line_1 == "ABC Street"
