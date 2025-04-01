"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.urls import reverse

from seed.models import OrganizationUser
from seed.test_helpers.fake import (
    FakeColumnListProfileFactory,
    FakeCycleFactory,
)
from seed.tests.util import AccessLevelBaseTestCase


class OrganizationUserViewTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.org_user = OrganizationUser.objects.get(organization=self.org, user=self.superuser)
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.superuser)
        self.profile_factory = FakeColumnListProfileFactory(organization=self.org)

        self.cycle1 = self.cycle_factory.get_cycle()
        self.cycle2 = self.cycle_factory.get_cycle()

        self.profile1 = self.profile_factory.get_columnlistprofile()
        self.profile2 = self.profile_factory.get_columnlistprofile()

    def test_update_settings(self):
        # real filters and sorts will be appended with an id: "pm_property_id_123"
        filters = {"pm_property_id": {"filter": "1", "filterType": "text", "type": "contains"}}
        sorts = ["pm_property_id", "-custom_id_1"]
        data = {"settings": {"cycle": self.cycle1.pk, "profile": self.profile2.pk, "sorts": sorts, "filters": filters}}
        url = reverse("api:v4:organization_users-detail", args=[self.org_user.pk]) + f"?organization_id={self.org.pk}"

        response = self.client.put(url, data=data, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(set(data.keys()), {"settings", "role_level", "status", "organization", "user", "email", "first_name", "last_name"})
        self.assertEqual(data["role_level"], 20)

        self.org_user.refresh_from_db()
        self.assertEqual(self.org_user.settings["cycle"], self.cycle1.pk)
        self.assertEqual(self.org_user.settings["profile"], self.profile2.pk)
        self.assertEqual(self.org_user.settings["sorts"], sorts)
        self.assertEqual(self.org_user.settings["filters"], filters)
        self.assertEqual(self.org_user.role_level, 20)

        # passing data without settings resets settings
        data = {"role_level": 10}
        response = self.client.put(url, data=data, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.org_user.refresh_from_db()
        self.assertEqual(self.org_user.settings, {})
        self.assertEqual(self.org_user.role_level, 10)
