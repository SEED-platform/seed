"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
from datetime import datetime
from os import path

from django.urls import reverse
from django.utils import timezone

from config.settings.common import BASE_DIR
from seed.landing.models import SEEDUser as User
from seed.models import ColumnMappingProfile, PropertyMeasure, PropertyView, StatusLabel
from seed.test_helpers.fake import (
    FakeColumnFactory,
    FakeCycleFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakeTaxLotStateFactory,
)
from seed.tests.util import DeleteModelsTestCase
from seed.utils.organizations import create_organization


class InventoryViewTests(DeleteModelsTestCase):
    def setUp(self):
        user_details = {"username": "test_user@demo.com", "password": "test_pass", "email": "test_user@demo.com"}
        self.user = User.objects.create_superuser(**user_details)
        self.org, _, _ = create_organization(self.user)
        self.status_label = StatusLabel.objects.create(name="test", super_organization=self.org)

        self.column_factory = FakeColumnFactory(organization=self.org)
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

        self.cycle = self.cycle_factory.get_cycle(start=datetime(2010, 10, 10, tzinfo=timezone.get_current_timezone()))

        self.default_bsync_profile = ColumnMappingProfile.objects.get(profile_type=ColumnMappingProfile.BUILDINGSYNC_DEFAULT)

        self.client.login(**user_details)

    def test_get_building_sync(self):
        state = self.property_state_factory.get_property_state()
        prprty = self.property_factory.get_property()
        pv = PropertyView.objects.create(property=prprty, cycle=self.cycle, state=state)

        # go to buildingsync endpoint
        params = {"organization_id": self.org.pk, "profile_id": self.default_bsync_profile.id}
        url = reverse("api:v3:properties-building-sync", args=[pv.id])
        response = self.client.get(url, params)
        self.assertIn(f"<auc:FloorAreaValue>{state.gross_floor_area}.0</auc:FloorAreaValue>", response.content.decode("utf-8"))

    def test_upload_and_get_building_sync(self):
        filename = path.join(path.dirname(__file__), "data", "ex_1.xml")

        url = reverse("api:v3:building_files-list") + f"?organization_id={self.org.id}&cycle_id={self.cycle.id}"
        with open(filename, "rb") as f:
            response = self.client.post(
                url,
                {
                    "file": f,
                    "file_type": "BuildingSync",
                },
            )

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], {"warnings": []})
        self.assertEqual(result["data"]["property_view"]["state"]["year_built"], 1967)
        self.assertEqual(result["data"]["property_view"]["state"]["postal_code"], "94111")

        # now get the building sync that was just uploaded
        property_id = result["data"]["property_view"]["id"]
        url = reverse("api:v3:properties-building-sync", args=[property_id])
        response = self.client.get(url, {"organization_id": self.org.pk, "profile_id": self.default_bsync_profile.id})
        self.assertIn("<auc:YearOfConstruction>1967</auc:YearOfConstruction>", response.content.decode("utf-8"))

    def test_upload_measures_specific_version(self):
        filename = path.join(path.dirname(__file__), "data", "ex_1_v2.6.0.xml")

        url = reverse("api:v3:building_files-list") + f"?organization_id={self.org.id}&cycle_id={self.cycle.id}"
        with open(filename, "rb") as f:
            response = self.client.post(
                url,
                {
                    "file": f,
                    "file_type": "BuildingSync",
                },
            )

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertEqual(result["status"], "success")

        # now get the building sync that was just uploaded
        property_state_id = result["data"]["property_view"]["state"]["id"]
        # check that the property measures associated with this upload link to
        # measures with schema_version v2.6.0
        pms = PropertyMeasure.objects.filter(property_state_id=property_state_id)
        self.assertEqual(len(pms), 1)
        self.assertEqual(pms[0].measure.schema_version, "2.6.0")
        self.assertEqual(pms[0].measure.category, "service_hot_water_systems")
        self.assertEqual(pms[0].measure.name, "install_heat_pump_shw_system")

    def test_upload_batch_building_sync(self):
        # import a zip file of BuildingSync xmls
        # import_record =
        filename = path.join(BASE_DIR, "seed", "building_sync", "tests", "data", "ex_1_and_buildingsync_ex01_measures.zip")

        url = f"/api/v3/building_files/?organization_id={self.org.id}&cycle_id={self.cycle.id}"
        with open(filename, "rb") as f:
            response = self.client.post(
                url,
                {
                    "file": f,
                    "file_type": "BuildingSync",
                },
            )

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)

        self.assertEqual(result["success"], True, f"Unexpected result: {result}")
        self.assertEqual(result["message"], {"warnings": []})
        self.assertEqual(result["data"]["property_view"]["state"]["year_built"], 1967)
        self.assertEqual(result["data"]["property_view"]["state"]["postal_code"], "94111")

    def test_upload_with_measure_duplicates(self):
        # import_record =
        filename = path.join(BASE_DIR, "seed", "building_sync", "tests", "data", "buildingsync_ex01_measures_bad_names.xml")

        url = reverse("api:v3:building_files-list") + f"?organization_id={self.org.id}&cycle_id={self.cycle.id}"
        with open(filename, "rb") as f:
            response = self.client.post(
                url,
                {
                    "file": f,
                    "file_type": "BuildingSync",
                },
            )

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertEqual(result["status"], "success")
        expected_message = {
            "warnings": [
                "Measure category and name is not valid other_electric_motors_and_drives:replace_with_higher_efficiency_bad_name for schema version 1.0.0",
                "Measure category and name is not valid other_hvac:install_demand_control_ventilation_bad_name for schema version 1.0.0",
                "Measure associated with scenario not found. Scenario: Replace with higher efficiency Only, Measure name: Measure22",
                "Measure associated with scenario not found. Scenario: Install demand control ventilation Only, Measure name: Measure24",
            ]
        }
        self.assertEqual(result["message"], expected_message)
        self.assertEqual(len(result["data"]["property_view"]["state"]["measures"]), 28)
        self.assertEqual(len(result["data"]["property_view"]["state"]["scenarios"]), 31)
        self.assertEqual(result["data"]["property_view"]["state"]["year_built"], 1967)
        self.assertEqual(result["data"]["property_view"]["state"]["postal_code"], "94111")

        # upload the same file again
        url = reverse("api:v3:building_files-list") + f"?organization_id={self.org.id}&cycle_id={self.cycle.id}"
        with open(filename, "rb") as f:
            response = self.client.post(
                url,
                {
                    "file": f,
                    "file_type": "BuildingSync",
                },
            )

        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)

        self.assertEqual(len(result["data"]["property_view"]["state"]["measures"]), 28)
        self.assertEqual(len(result["data"]["property_view"]["state"]["scenarios"]), 31)

    def test_upload_and_get_building_sync_diff_ns(self):
        filename = path.join(path.dirname(__file__), "data", "ex_1_different_namespace.xml")

        url = reverse("api:v3:building_files-list") + f"?organization_id={self.org.id}&cycle_id={self.cycle.id}"

        with open(filename, "rb") as f:
            response = self.client.post(
                url,
                {
                    "file": f,
                    "file_type": "BuildingSync",
                },
            )

        result = json.loads(response.content)
        self.assertEqual(response.status_code, 200, f"Expected 200 response. Message body: {result}")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], {"warnings": []})
        self.assertEqual(result["data"]["property_view"]["state"]["year_built"], 1889)

        # now get the building sync that was just uploaded
        property_id = result["data"]["property_view"]["id"]
        url = reverse("api:v3:properties-building-sync", args=[property_id])
        response = self.client.get(url, {"organization_id": self.org.pk, "profile_id": self.default_bsync_profile.id})
        self.assertIn("<auc:YearOfConstruction>1889</auc:YearOfConstruction>", response.content.decode("utf-8"))
