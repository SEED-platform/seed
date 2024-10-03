"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
from datetime import datetime

import pytz
from django.urls import reverse
from xlrd import open_workbook

from seed.data_importer.models import ImportFile, ImportRecord
from seed.landing.models import SEEDUser as User
from seed.lib.mcm.reader import ROW_DELIMITER
from seed.models import Column, Cycle, FilterGroup, PropertyView
from seed.models import StatusLabel as Label
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
)
from seed.tests.util import AccessLevelBaseTestCase, DataMappingBaseTestCase
from seed.utils.organizations import create_organization


class TestOrganizationViews(DataMappingBaseTestCase):
    def setUp(self):
        user_details = {
            "username": "test_user@demo.com",
            "password": "test_pass",
        }
        user = User.objects.create_superuser(email="test_user@demo.com", **user_details)
        self.org, _, _ = create_organization(user)

        self.client.login(**user_details)

    def test_matching_criteria_columns_view(self):
        url = reverse("api:v3:organizations-matching-criteria-columns", args=[self.org.id])
        raw_result = self.client.get(url)
        result = json.loads(raw_result.content)

        default_matching_criteria_display_names = {
            "PropertyState": [
                "custom_id_1",
                "pm_property_id",
            ],
            "TaxLotState": [
                "custom_id_1",
                "jurisdiction_tax_lot_id",
            ],
        }

        self.assertCountEqual(result["PropertyState"], default_matching_criteria_display_names["PropertyState"])
        self.assertCountEqual(result["TaxLotState"], default_matching_criteria_display_names["TaxLotState"])

    def test_matching_criteria_columns_view_with_nondefault_geocoding_columns(self):
        # Deactivate city for properties and state for taxlots
        self.org.column_set.filter(column_name="city", table_name="PropertyState").update(geocoding_order=0)
        self.org.column_set.filter(column_name="state", table_name="TaxLotState").update(geocoding_order=0)

        # Create geocoding-enabled ED_city for properties and ED_state for taxlots
        self.org.column_set.create(column_name="ed_city", is_extra_data=True, table_name="PropertyState", geocoding_order=3)
        self.org.column_set.create(column_name="ed_state", is_extra_data=True, table_name="TaxLotState", geocoding_order=4)

        url = reverse("api:v3:organizations-geocoding-columns", args=[self.org.id])
        raw_result = self.client.get(url)
        result = json.loads(raw_result.content)

        default_matching_criteria_display_names = {
            "PropertyState": [
                "address_line_1",
                "address_line_2",
                "ed_city",
                "state",
                "postal_code",
            ],
            "TaxLotState": [
                "address_line_1",
                "address_line_2",
                "city",
                "ed_state",
                "postal_code",
            ],
        }

        # Specifically use assertEqual as order does matter
        self.assertEqual(result["PropertyState"], default_matching_criteria_display_names["PropertyState"])
        self.assertEqual(result["TaxLotState"], default_matching_criteria_display_names["TaxLotState"])


class TestOrganizationPermissions(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.import_record = ImportRecord.objects.create(
            owner=self.root_owner_user,
            super_organization=self.org,
            access_level_instance=self.org.root,
        )
        self.import_file = ImportFile.objects.create(
            import_record=self.import_record,
            source_type="Assessed Raw",
            mapping_done=True,
            cached_first_row=ROW_DELIMITER.join(["name", "address", "year built", "building id"]),
        )

        self.property = self.property_factory.get_property()
        self.property_view = self.property_view_factory.get_property_view(prprty=self.property, cycle=Cycle.objects.first())

    def test_column_mappings(self):
        url = reverse("api:v3:organizations-column-mappings", args=[self.org.pk]) + f"?import_file_id={self.import_file.id}"
        params = json.dumps({"mappings": []})

        # child user cannot
        self.login_as_child_member()
        resp = self.client.post(url, params, content_type="application/json")
        assert resp.status_code == 404

        # root users can
        self.login_as_root_member()
        response = self.client.post(url, params, content_type="application/json")
        assert response.status_code == 200

    def test_column_mappings_creates_new_column(self):
        self.import_record.access_level_instance = self.child_level_instance
        self.import_record.save()
        url = reverse("api:v3:organizations-column-mappings", args=[self.org.pk]) + f"?import_file_id={self.import_file.id}"
        params = json.dumps(
            {
                "mappings": [
                    {
                        "from_field": "a new col",
                        "from_units": None,
                        "to_field": "a new col",
                        "to_field_display_name": "a new col",
                        "to_table_name": "PropertyState",
                    }
                ]
            }
        )

        # child user cannot
        self.login_as_child_member()
        resp = self.client.post(url, params, content_type="application/json")
        assert resp.status_code == 200
        assert resp.json() == {"status": "error", "message": "user does not have permission to create column a new col"}

        # root users can
        self.login_as_root_member()
        response = self.client.post(url, params, content_type="application/json")
        assert response.status_code == 200
        assert response.json() == {"status": "success"}

    def test_columns_delete(self):
        url = reverse("api:v3:organizations-columns", args=[self.org.pk])

        # child user cannot
        self.login_as_child_member()
        resp = self.client.delete(url, content_type="application/json")
        assert resp.status_code == 403

        # root owner can
        self.login_as_root_owner()
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 200

    def test_report(self):
        url = reverse("api:v3:organizations-report", args=[self.org.pk])
        url += f"?x_var=building_count&y_var=gross_floor_area&cycle_ids={Cycle.objects.first().id}"

        # child user cannot
        self.login_as_child_member()
        resp = self.client.get(url, content_type="application/json")
        assert resp.json()["data"]["property_counts"][0]["num_properties"] == 0

        # root users can
        self.login_as_root_member()
        resp = self.client.get(url, content_type="application/json")
        assert resp.json()["data"]["property_counts"][0]["num_properties"] == 1

        # root users can choose
        self.login_as_root_member()
        resp = self.client.get(url + "&access_level_instance_id=" + str(self.child_level_instance.pk), content_type="application/json")
        assert resp.json()["data"]["property_counts"][0]["num_properties"] == 0

        # child user cannot choose
        self.login_as_child_member()
        resp = self.client.get(url + "&access_level_instance_id=" + str(self.root_level_instance.pk), content_type="application/json")
        assert resp.status_code == 400

    def test_report_aggregated(self):
        url = reverse("api:v3:organizations-report-aggregated", args=[self.org.pk])
        url += f"?x_var=building_count&y_var=gross_floor_area&cycle_ids={Cycle.objects.first().id}"

        # child user cannot
        self.login_as_child_member()
        resp = self.client.get(url + "&access_level_instance_id=" + str(self.child_level_instance.pk), content_type="application/json")
        assert resp.json()["aggregated_data"]["property_counts"][0]["num_properties"] == 0

        # root users can
        self.login_as_root_member()
        resp = self.client.get(url + "&access_level_instance_id=" + str(self.root_level_instance.pk), content_type="application/json")
        assert resp.json()["aggregated_data"]["property_counts"][0]["num_properties"] == 1

    def test_report_export(self):
        url = reverse("api:v3:organizations-report-export", args=[self.org.pk])
        url += f"?x_var=building_count&y_var=gross_floor_area&cycle_ids={Cycle.objects.first().id}"
        url += "&x_label=x&y_label=y"

        # child user cannot
        self.login_as_child_member()
        resp = self.client.get(url, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        wb = open_workbook(file_contents=resp.content)
        assert wb.sheet_by_index(0).cell(1, 2).value == 0.0

        # root users can
        self.login_as_root_member()
        resp = self.client.get(url, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        wb = open_workbook(file_contents=resp.content)
        assert wb.sheet_by_index(0).cell(1, 2).value == 1.0


class TestOrganizationViewsWithFilters(AccessLevelBaseTestCase):
    """
    Test DataView model's ability to return property views based on filter groups
    """

    def setUp(self):
        user_details = {
            "username": "test_user@demo.com",
            "password": "test_pass",
            "email": "test_user@demo.com",
            "first_name": "Johnny",
            "last_name": "Energy",
        }
        self.superuser = User.objects.create_superuser(**user_details)
        self.org, _, _ = create_organization(self.superuser, "test-organization-a")
        self.client.login(**user_details)
        self.cycle1 = FakeCycleFactory(organization=self.org, user=self.superuser).get_cycle(
            name="Cycle A", end=datetime(2022, 1, 1, tzinfo=pytz.UTC)
        )

        self.label1 = Label.objects.create(name="label1", super_organization=self.org, color="red")
        self.label2 = Label.objects.create(name="label2", super_organization=self.org, color="blue")

        # generate columns
        self.site_eui = Column.objects.get(column_name="site_eui")

        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)

        # generate two different types of properties
        self.office1 = self.property_factory.get_property()
        self.office2 = self.property_factory.get_property()

        # generate property states that are either 'Office' or 'Retail' for filter groups
        # generate property views that are attached to a property and a property-state
        self.state10 = self.property_state_factory.get_property_state(property_name="state10", property_type="office", site_eui=0)
        self.state11 = self.property_state_factory.get_property_state(property_name="state11", property_type="office", site_eui=12)

        self.view10 = PropertyView.objects.create(property=self.office1, cycle=self.cycle1, state=self.state10)
        self.view11 = PropertyView.objects.create(property=self.office2, cycle=self.cycle1, state=self.state11)

        site_eui_id = Column.objects.get(table_name="PropertyState", column_name="site_eui").id
        property_type_id = Column.objects.get(table_name="PropertyState", column_name="property_type").id
        self.office_filter_group = FilterGroup.objects.create(
            name="office",
            organization_id=self.org.id,
            inventory_type=0,  # Property
            query_dict={f"property_type_{property_type_id}__exact": "office", f"site_eui_{site_eui_id}__gt": 1},
        )
        self.office_filter_group.save()

    def test_filtered_report(self):
        url = reverse("api:v3:organizations-report", args=[self.org.pk])
        url += f"?x_var=building_count&y_var=gross_floor_area&cycle_ids={self.cycle1.id}"

        # Unfiltered report
        resp = self.client.get(url, content_type="application/json")
        assert resp.json()["data"]["property_counts"][0]["num_properties"] == 2

        url += f"&filter_group_id={self.office_filter_group.id}"
        resp = self.client.get(url, content_type="application/json")
        assert resp.json()["data"]["property_counts"][0]["num_properties"] == 1
