"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
from datetime import UTC, datetime

from django.test import TransactionTestCase
from django.urls import reverse

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import ROLE_MEMBER
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
            name="Cycle A", end=datetime(2022, 1, 1, tzinfo=UTC)
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

    def test_update_and_delete_are_scoped_to_organization(self):
        other_report_configuration = ReportConfiguration.objects.create(name="other_report_config", organization_id=self.other_org.id)
        url = reverse("api:v3:report_configurations-detail", args=[other_report_configuration.id]) + f"?organization_id={self.org.id}"

        # a root member of this organization only
        member_details = {"username": "member@demo.com", "password": "test_pass"}
        member = User.objects.create_user(**member_details)
        self.org.add_member(member, self.org.root.id, ROLE_MEMBER)
        self.client.login(**member_details)

        # another organization's report configuration cannot be updated or deleted
        response = self.client.put(url, data=json.dumps({"name": "hijacked"}), content_type="application/json")
        self.assertEqual(404, response.status_code)
        response = self.client.delete(url, content_type="application/json")
        self.assertEqual(400, response.status_code)
        other_report_configuration.refresh_from_db()
        self.assertEqual("other_report_config", other_report_configuration.name)

        # within the organization, a missing report configuration is not found
        url = reverse("api:v3:report_configurations-detail", args=[0]) + f"?organization_id={self.org.id}"
        response = self.client.put(url, data=json.dumps({"name": "missing"}), content_type="application/json")
        self.assertEqual(404, response.status_code)

        # the organization's own report configuration can be updated
        url = reverse("api:v3:report_configurations-detail", args=[self.report_configuration.id]) + f"?organization_id={self.org.id}"
        response = self.client.put(url, data=json.dumps({"name": "renamed"}), content_type="application/json")
        self.assertEqual(200, response.status_code)
        self.report_configuration.refresh_from_db()
        self.assertEqual("renamed", self.report_configuration.name)

    def test_create_and_update_reject_another_organizations_data(self):
        other_cycle = FakeCycleFactory(organization=self.other_org, user=self.user).get_cycle(
            name="Other Cycle", end=datetime(2022, 1, 1, tzinfo=UTC)
        )
        other_filter_group = FilterGroup.objects.create(
            name="other_filter_group", organization_id=self.other_org.id, inventory_type=1, query_dict={}
        )
        list_url = reverse("api:v3:report_configurations-list") + f"?organization_id={self.org.id}"
        detail_url = reverse("api:v3:report_configurations-detail", args=[self.report_configuration.id]) + f"?organization_id={self.org.id}"

        # another organization's access level instance or filter group is rejected, like a nonexistent one
        for body in [{"access_level_instance_id": self.other_org.root.id}, {"filter_group_id": other_filter_group.id}]:
            response = self.client.post(list_url, data=json.dumps({"name": "other", **body}), content_type="application/json")
            self.assertEqual(400, response.status_code)
            response = self.client.put(detail_url, data=json.dumps(body), content_type="application/json")
            self.assertEqual(400, response.status_code)
        self.assertFalse(ReportConfiguration.objects.filter(name="other").exists())

        # another organization's cycles are ignored, like nonexistent ones
        response = self.client.post(
            list_url, data=json.dumps({"name": "other", "cycles": [self.cycle1.id, other_cycle.id]}), content_type="application/json"
        )
        self.assertEqual(201, response.status_code)
        self.assertEqual([self.cycle1.id], response.json()["data"]["cycles"])
        response = self.client.put(detail_url, data=json.dumps({"cycles": [other_cycle.id]}), content_type="application/json")
        self.assertEqual(200, response.status_code)
        self.assertFalse(self.report_configuration.cycles.exists())

        # the organization's own data is accepted
        body = {"name": "own", "access_level_instance_id": self.org.root.id, "filter_group_id": self.filter_group.id}
        response = self.client.post(list_url, data=json.dumps(body), content_type="application/json")
        self.assertEqual(201, response.status_code)
        response = self.client.put(detail_url, data=json.dumps(body), content_type="application/json")
        self.assertEqual(200, response.status_code)
        self.report_configuration.refresh_from_db()
        self.assertEqual(self.org.root.id, self.report_configuration.access_level_instance_id)
        self.assertEqual(self.filter_group.id, self.report_configuration.filter_group_id)
