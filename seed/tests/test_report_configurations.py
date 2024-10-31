"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
from datetime import datetime

import pytz
from django.test import TransactionTestCase
from django.urls import reverse

from seed.landing.models import SEEDUser as User
from seed.models import FilterGroup, ReportConfiguration
from seed.test_helpers.fake import (
    FakeCycleFactory,
)
from seed.utils.organizations import create_organization


class ReportConfigurationTests(TransactionTestCase):
    def setUp(self):
        user_details = {
            "username": "test_user@demo.com",  # the username needs to be in the form of an email.
            "password": "test_pass",
            "email": "test_user@demo.com",
            "first_name": "Jaqen",
            "last_name": "H'ghar",
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, _, _ = create_organization(self.user, "test-organization-a")
        self.other_org, _, _ = create_organization(self.user, "test-organization-b")
        self.client.login(**user_details)
        self.cycle1 = FakeCycleFactory(organization=self.org, user=self.user).get_cycle(
            name="Cycle A", end=datetime(2022, 1, 1, tzinfo=pytz.UTC)
        )

        self.filter_group = FilterGroup.objects.create(
            name="test_filter_group",
            organization_id=self.org.id,
            inventory_type=1,  # Tax Lot
            query_dict={"year_built__lt": ["1950"]},
        )
        self.filter_group.save()
        self.report_configuration = ReportConfiguration.objects.create(name="blank_report_config", organization_id=self.org.id)
        self.report_configuration.save()

    def test_create_report_configuration(self):
        # Action
        response = self.client.post(
            reverse("api:v3:report_configurations-list") + f"?organization_id={self.org.id}",
            data=json.dumps(
                {
                    "name": "new_report_config",
                }
            ),
            content_type="application/json",
        )

        # Assertion
        self.assertEqual(201, response.status_code)
        self.assertEqual(response.json()["status"], "success")

        data = response.json()["data"]
        self.assertIsInstance(data["id"], int)
        self.assertEqual("new_report_config", data["name"])

    def test_update_cycles(self):
        response = self.client.put(
            reverse("api:v3:report_configurations-detail", args=[self.report_configuration.id]) + f"?organization_id={self.org.id}",
            data=json.dumps({"cycles": [self.cycle1.id]}),
            content_type="application/json",
        )
        self.assertEqual(200, response.status_code)
        rc = ReportConfiguration.objects.get(pk=self.report_configuration.id)
        self.assertListEqual(list(rc.cycles.all()), [self.cycle1])

    def test_update_with_bad_cycle(self):
        response = self.client.put(
            reverse("api:v3:report_configurations-detail", args=[self.report_configuration.id]) + f"?organization_id={self.org.id}",
            data=json.dumps({"cycles": [10000000]}),
            content_type="application/json",
        )
        self.assertEqual(200, response.status_code)
        rc = ReportConfiguration.objects.get(pk=self.report_configuration.id)
        self.assertListEqual([], list(rc.cycles.all()))

    def test_update_columns(self):
        response = self.client.put(
            reverse("api:v3:report_configurations-detail", args=[self.report_configuration.id]) + f"?organization_id={self.org.id}",
            data=json.dumps({"x_column": "some_column", "y_column": "some_other_column"}),
            content_type="application/json",
        )
        self.assertEqual(200, response.status_code)
        rc = ReportConfiguration.objects.get(pk=self.report_configuration.id)
        self.assertEqual("some_column", rc.x_column)
        self.assertEqual("some_other_column", rc.y_column)

    def test_delete(self):
        response = self.client.delete(
            reverse("api:v3:report_configurations-detail", args=[self.report_configuration.id]) + f"?organization_id={self.org.id}",
            content_type="application/json",
        )

        self.assertEqual(204, response.status_code)
