"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json

from django.urls import reverse, reverse_lazy
from rest_framework import status

from seed.landing.models import SEEDUser as User
from seed.models import VIEW_LIST_TAXLOT, Column
from seed.models.derived_columns import DerivedColumn
from seed.test_helpers.fake import (
    FakeColumnListProfileFactory,
    FakeCycleFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
    FakeTaxLotStateFactory,
    FakeTaxLotViewFactory,
)
from seed.tests.util import AccessLevelBaseTestCase, DeleteModelsTestCase
from seed.utils.organizations import create_organization


class ColumnListProfilesView(DeleteModelsTestCase):
    """
    Tests of the SEED default custom saved columns
    """

    def setUp(self):
        user_details = {"username": "test_user@demo.com", "password": "test_pass", "email": "test_user@demo.com"}
        self.user = User.objects.create_superuser(**user_details)
        self.org, _, _ = create_organization(self.user, "test-organization-a")

        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.cycle = self.cycle_factory.get_cycle()

        self.column_list_factory = FakeColumnListProfileFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org, cycle=self.cycle)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_view_factory = FakeTaxLotViewFactory(organization=self.org, cycle=self.cycle)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

        self.column_1 = Column.objects.get(organization=self.org, table_name="PropertyState", column_name="address_line_1")
        self.column_2 = Column.objects.get(organization=self.org, table_name="PropertyState", column_name="city")
        self.column_3 = Column.objects.create(
            organization=self.org, table_name="PropertyState", column_name="extra data 1", is_extra_data=True
        )
        self.payload_data = {
            "name": "Test Column List Setting",
            "profile_location": "List View Profile",
            "inventory_type": "Property",
            "columns": [
                {
                    "id": self.column_1.id,
                    "pinned": False,
                    "order": 1,
                    "column_name": self.column_1.column_name,
                    "table_name": self.column_1.table_name,
                },
                {
                    "id": self.column_2.id,
                    "pinned": False,
                    "order": 2,
                    "column_name": self.column_2.column_name,
                    "table_name": self.column_2.table_name,
                },
                {
                    "id": self.column_3.id,
                    "pinned": True,
                    "order": 3,
                    "column_name": self.column_3.column_name,
                    "table_name": self.column_3.table_name,
                },
            ],
            "derived_columns": [],
        }
        self.client.login(**user_details)

    def test_create_column_profile(self):
        response = self.client.post(
            reverse("api:v3:column_list_profiles-list") + "?organization_id=" + str(self.org.id),
            data=json.dumps(self.payload_data),
            content_type="application/json",
        )
        data = json.loads(response.content)
        self.assertEqual(data["status"], "success")
        self.assertEqual(len(data["data"]["columns"]), 3)
        self.assertEqual(data["data"]["inventory_type"], "Property")
        self.assertEqual(data["data"]["profile_location"], "List View Profile")

    def test_create_column_profile_with_derived_column(self):
        self.derived_column = DerivedColumn.objects.create(
            name="dc",
            expression="$a + 10",
            organization=self.org,
            inventory_type=0,
        )
        self.payload_data["derived_columns"].append(
            {
                "column_name": "dc",
                "derived_column": True,
                "id": self.derived_column.id,
                "order": 4,
                "pinned": False,
                "table_name": "PropertyState",
            }
        )

        response = self.client.post(
            reverse("api:v3:column_list_profiles-list") + "?organization_id=" + str(self.org.id),
            data=json.dumps(self.payload_data),
            content_type="application/json",
        )
        data = json.loads(response.content)
        self.assertEqual(data["status"], "success")
        self.assertEqual(len(data["data"]["columns"]), 3)
        self.assertEqual(len(data["data"]["derived_columns"]), 1)
        self.assertEqual(data["data"]["inventory_type"], "Property")
        self.assertEqual(data["data"]["profile_location"], "List View Profile")

    def test_get_column_profile(self):
        # Create two list settings
        self.client.post(
            reverse("api:v3:column_list_profiles-list") + "?organization_id=" + str(self.org.id),
            data=json.dumps(self.payload_data),
            content_type="application/json",
        )
        self.client.post(
            reverse("api:v3:column_list_profiles-list") + "?organization_id=" + str(self.org.id),
            data=json.dumps(self.payload_data),
            content_type="application/json",
        )

        response = self.client.get(reverse("api:v3:column_list_profiles-list") + "?organization_id=" + str(self.org.id))
        data = json.loads(response.content)
        self.assertEqual(len(data["data"]), 2)

        # test getting a single one
        id = data["data"][0]["id"]
        response = self.client.get(reverse("api:v3:column_list_profiles-detail", args=[id]) + "?organization_id=" + str(self.org.id))
        data = json.loads(response.content)
        self.assertEqual(data["data"]["id"], id)
        self.assertEqual(len(data["data"]["columns"]), 3)

    def test_delete_column_profile(self):
        # Create two list settings
        to_delete = self.client.post(
            reverse("api:v3:column_list_profiles-list") + "?organization_id=" + str(self.org.id),
            data=json.dumps(self.payload_data),
            content_type="application/json",
        )
        self.client.post(
            reverse("api:v3:column_list_profiles-list") + "?organization_id=" + str(self.org.id),
            data=json.dumps(self.payload_data),
            content_type="application/json",
        )
        id_to_delete = json.loads(to_delete.content)["data"]["id"]
        response = self.client.delete(
            reverse("api:v3:column_list_profiles-detail", args=[id_to_delete]) + "?organization_id=" + str(self.org.id)
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # check to make sure that it isn't in the column list setting list.
        response = self.client.get(reverse("api:v3:column_list_profiles-list") + "?organization_id=" + str(self.org.id))
        data = json.loads(response.content)
        self.assertEqual(len(data["data"]), 1)
        self.assertNotEqual(data["data"][0]["id"], id_to_delete)

    def test_update_column_profile(self):
        cls = self.client.post(
            reverse("api:v3:column_list_profiles-list") + "?organization_id=" + str(self.org.id),
            data=json.dumps(self.payload_data),
            content_type="application/json",
        )
        payload = {
            "name": "New Name",
            "inventory_type": "Tax Lot",
            "profile_location": "List View Profile",
            "columns": [],
            "derived_columns": [],
        }
        url = (
            reverse("api:v3:column_list_profiles-detail", args=[json.loads(cls.content)["data"]["id"]])
            + "?organization_id="
            + str(self.org.id)
        )

        response = self.client.put(url, data=json.dumps(payload), content_type="application/json")
        result = json.loads(response.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The columns will be removed if you don't specify them again in an update method
        self.assertEqual(result["data"]["inventory_type"], "Tax Lot")
        self.assertEqual(len(result["data"]["columns"]), 0)

        payload["columns"] = [
            {
                "id": self.column_1.id,
                "pinned": True,
                "order": 999,
                "column_name": self.column_3.column_name,
                "table_name": self.column_3.table_name,
            }
        ]
        response = self.client.put(url, data=json.dumps(payload), content_type="application/json")
        result = json.loads(response.content)
        self.assertEqual(len(result["data"]["columns"]), 1)
        self.assertEqual(result["data"]["columns"][0]["order"], 999)
        self.assertEqual(result["data"]["columns"][0]["pinned"], True)

    def test_column_profile_show_populated(self):
        # Set Up
        columnlistprofile = self.column_list_factory.get_columnlistprofile(columns=["address_line_1", "city"])
        state = self.property_state_factory.get_property_state(no_default_data=True, city="Denver")
        self.property_view_factory.get_property_view(state=state)

        # Action
        response = self.client.put(
            reverse("api:v3:column_list_profiles-show-populated", args=[columnlistprofile.id]) + f"?organization_id={self.org.id}",
            data=json.dumps({"cycle_id": self.cycle.id, "inventory_type": "Property"}),
            content_type="application/json",
        )
        result = json.loads(response.content)

        # Assertion
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        columns = {c["column_name"] for c in result["data"]["columns"]}
        self.assertSetEqual(columns, {"city", "updated", "created"})

    def test_column_profile_show_populated_taxlots(self):
        columnlistprofile = self.column_list_factory.get_columnlistprofile(
            columns=["address_line_1", "city"], inventory_type=VIEW_LIST_TAXLOT
        )
        state = self.taxlot_state_factory.get_taxlot_state(no_default_data=True, longitude=12345)
        self.taxlot_view_factory.get_taxlot_view(state=state)

        response = self.client.put(
            reverse("api:v3:column_list_profiles-show-populated", args=[columnlistprofile.id]) + f"?organization_id={self.org.id}",
            data=json.dumps({"cycle_id": self.cycle.id, "inventory_type": "Tax Lot"}),
            content_type="application/json",
        )
        result = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        columns = {c["column_name"] for c in result["data"]["columns"]}
        self.assertSetEqual(columns, {"updated", "longitude", "created"})

    def test_column_profile_show_populated_extra_data(self):
        # Set Up
        columnlistprofile = self.column_list_factory.get_columnlistprofile(columns=["address_line_1", "city"])
        state = self.property_state_factory.get_property_state(no_default_data=True, extra_data={self.column_3.column_name: "Denver"})
        self.property_view_factory.get_property_view(state=state)

        # Action
        response = self.client.put(
            reverse("api:v3:column_list_profiles-show-populated", args=[columnlistprofile.id]) + f"?organization_id={self.org.id}",
            data=json.dumps({"cycle_id": self.cycle.id, "inventory_type": "Property"}),
            content_type="application/json",
        )
        result = json.loads(response.content)

        # Assertion
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        columns = {c["column_name"] for c in result["data"]["columns"]}
        self.assertSetEqual(columns, {self.column_3.column_name, "updated", "created"})

    def test_column_profile_show_populated_derived_data(self):
        # Set Up
        self.derived_column = DerivedColumn.objects.create(name="dc", expression="$a + 10", organization=self.org, inventory_type=0)
        columnlistprofile = self.column_list_factory.get_columnlistprofile(columns=["address_line_1", "city"])
        state = self.property_state_factory.get_property_state(
            no_default_data=True, derived_data={self.derived_column.column.column_name: "20"}
        )
        self.property_view_factory.get_property_view(state=state)

        # Action
        response = self.client.put(
            reverse("api:v3:column_list_profiles-show-populated", args=[columnlistprofile.id]) + f"?organization_id={self.org.id}",
            data=json.dumps({"cycle_id": self.cycle.id, "inventory_type": "Property"}),
            content_type="application/json",
        )
        result = json.loads(response.content)

        # Assertion
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        columns = {c["column_name"] for c in result["data"]["columns"]}
        self.assertSetEqual(columns, {self.derived_column.column.column_name, "updated", "created"})


class ColumnsListProfileViewPermissionsTests(AccessLevelBaseTestCase, DeleteModelsTestCase):
    def setUp(self):
        super().setUp()

        self.column_1 = Column.objects.get(organization=self.org, table_name="PropertyState", column_name="address_line_1")
        self.column_2 = Column.objects.get(organization=self.org, table_name="PropertyState", column_name="city")
        self.payload_data = {
            "name": "Test Column List Setting",
            "profile_location": "List View Profile",
            "inventory_type": "Property",
            "columns": [
                {
                    "id": self.column_1.id,
                    "pinned": False,
                    "order": 1,
                    "column_name": self.column_1.column_name,
                    "table_name": self.column_1.table_name,
                },
                {
                    "id": self.column_2.id,
                    "pinned": False,
                    "order": 2,
                    "column_name": self.column_2.column_name,
                    "table_name": self.column_2.table_name,
                },
            ],
            "derived_columns": [],
        }

        column_list_factory = FakeColumnListProfileFactory(organization=self.org)
        self.columnlistprofile = column_list_factory.get_columnlistprofile(columns=["address_line_1", "city"])

    def test_column_list_profile_create_permissions(self):
        url = reverse_lazy("api:v3:column_list_profiles-list") + "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.post(url, data=json.dumps(self.payload_data), content_type="application/json")
        assert response.status_code == 403

        # root users can create column in root
        self.login_as_root_member()
        response = self.client.post(url, data=json.dumps(self.payload_data), content_type="application/json")
        assert response.status_code == 201

    def test_column_list_profile_delete_permissions(self):
        url = reverse_lazy("api:v3:column_list_profiles-detail", args=[self.columnlistprofile.id]) + "?organization_id=" + str(self.org.id)

        # child user cannot
        self.login_as_child_member()
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 403

        # root users can
        self.login_as_root_owner()
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 204

    def test_column_list_profile_update_permissions(self):
        url = reverse_lazy("api:v3:column_list_profiles-detail", args=[self.columnlistprofile.id]) + "?organization_id=" + str(self.org.id)
        self.payload_data["name"] = "boo"

        # child user cannot
        self.login_as_child_member()
        response = self.client.put(url, data=json.dumps(self.payload_data), content_type="application/json")
        assert response.status_code == 403

        # root users can
        self.login_as_root_member()
        response = self.client.put(url, data=json.dumps(self.payload_data), content_type="application/json")
        assert response.status_code == 200
