"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:author nicholas.long@nrel.gov
"""

from django.test import TestCase
from django.urls import reverse

from seed.landing.models import SEEDUser as User
from seed.models import FacilitiesPlan
from seed.utils.organizations import create_organization


class FacilitiesPlanTests(TestCase):
    def setUp(self):
        user_details = {
            "username": "test_user@demo.com",
            "password": "test_pass",
        }
        self.user = User.objects.create_superuser(email="test_user@demo.com", **user_details)
        self.org, _, _ = create_organization(self.user)
        self.client.login(**user_details)

        self.facilities_plan = FacilitiesPlan.objects.create(organization=self.org, name="test", energy_running_sum_percentage=0.85)

    def test_list(self):
        response = self.client.get(
            reverse("api:v3:facilities_plans-list") + "?organization_id=" + str(self.org.id), content_type="application/json"
        )

        self.assertDictEqual(
            response.json(),
            {
                "status": "success",
                "data": [
                    {
                        "id": self.facilities_plan.id,
                        "organization": self.org.id,
                        "name": "test",
                        "energy_running_sum_percentage": 0.85,
                    }
                ],
            },
        )

    def test_retrieve(self):
        response = self.client.get(
            reverse("api:v3:facilities_plans-detail", args=[self.facilities_plan.id]) + "?organization_id=" + str(self.org.id),
            content_type="application/json",
        )

        print(response.json())
        self.assertDictEqual(
            response.json(),
            {
                "status": "success",
                "data": {
                    "id": self.facilities_plan.id,
                    "organization": self.org.id,
                    "name": "test",
                    "energy_running_sum_percentage": 0.85,
                },
            },
        )
