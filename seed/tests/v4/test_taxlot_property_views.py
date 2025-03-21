"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
from datetime import datetime

from django.urls import reverse
from django.utils.timezone import (
    get_current_timezone,
)

from seed.data_importer.tasks import geocode_and_match_buildings_task
from seed.landing.models import SEEDUser as User
from seed.models import (
    DATA_STATE_MAPPING,
    ColumnMappingProfile,
    Property,
    PropertyView,
    StatusLabel,
    TaxLotProperty,
    TaxLotView,
)
from seed.test_helpers.fake import (
    FakeColumnFactory,
    FakeColumnListProfileFactory,
    FakeCycleFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
    FakeTaxLotFactory,
    FakeTaxLotStateFactory,
)
from seed.tests.util import AccessLevelBaseTestCase, DataMappingBaseTestCase
from seed.utils.organizations import create_organization

COLUMNS_TO_SEND = [
    "project_id",
    "address_line_1",
    "city",
    "state_province",
    "postal_code",
    "pm_parent_property_id",
    "extra_data_field",
    "jurisdiction_tax_lot_id",
]


class TaxLotPropertyViewTests(DataMappingBaseTestCase):
    def setUp(self):
        user_details = {"username": "test_user@demo.com", "password": "test_pass", "email": "test_user@demo.com"}
        self.user = User.objects.create_superuser(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        self.column_factory = FakeColumnFactory(organization=self.org)
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.cycle = self.cycle_factory.get_cycle(start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))
        self.column_list_factory = FakeColumnListProfileFactory(organization=self.org)
        self.client.login(**user_details)

        # create tree
        self.org.access_level_names = ["1st Gen", "2nd Gen", "3rd Gen"]
        mom_ali = self.org.add_new_access_level_instance(self.org.root.id, "mom")
        self.me_ali = self.org.add_new_access_level_instance(mom_ali.id, "me")
        self.sister_ali = self.org.add_new_access_level_instance(mom_ali.id, "sister")
        self.org.save()

        _, import_file_1 = self.create_import_file(self.user, self.org, self.cycle)
        base_details = {
            "custom_id_1": "CustomID123",
            "import_file_id": import_file_1.id,
            "data_state": DATA_STATE_MAPPING,
            "no_default_data": False,
            "raw_access_level_instance_id": self.org.root.id,
        }
        self.property_state_factory.get_property_state(**base_details)

        # set import_file_1 mapping done so that record is "created for users to view".
        import_file_1.mapping_done = True
        import_file_1.save()
        geocode_and_match_buildings_task(import_file_1.id)

        _, import_file_2 = self.create_import_file(self.user, self.org, self.cycle)

        url = (
            reverse("api:v4:tax_lot_properties-filter")
            + f"?inventory_type=property&cycle_id={self.cycle.pk}&organization_id={self.org.pk}&page=1&per_page=999999999"
        )
        response = self.client.post(url, content_type="application/json")
        data = json.loads(response.content)

        self.assertFalse(data["results"][0]["merged_indicator"])

        # make sure merged_indicator is True when merge occurs
        base_details["city"] = "Denver"
        base_details["import_file_id"] = import_file_2.id
        self.property_state_factory.get_property_state(**base_details)

        # set import_file_2 mapping done so that match merging can occur.
        import_file_2.mapping_done = True
        import_file_2.save()
        geocode_and_match_buildings_task(import_file_2.id)

        # Create pairings and check if paired object has indicator as well
        taxlot_factory = FakeTaxLotFactory(organization=self.org)
        taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

        taxlot = taxlot_factory.get_taxlot()
        taxlot_state = taxlot_state_factory.get_taxlot_state()
        taxlot_view = TaxLotView.objects.create(taxlot=taxlot, cycle=self.cycle, state=taxlot_state)

        # attach pairing to one and only property_view
        TaxLotProperty(
            primary=True, cycle_id=self.cycle.id, property_view_id=PropertyView.objects.get().id, taxlot_view_id=taxlot_view.id
        ).save()

    def test_inventory_filter(self):
        url = (
            reverse("api:v4:tax_lot_properties-filter")
            + f"?inventory_type=property&cycle_id={self.cycle.pk}&organization_id={self.org.pk}&page=1&per_page=999999999"
        )
        response = self.client.post(url, content_type="application/json")
        data = json.loads(response.content)
        self.assertEqual(list(data.keys()), ["pagination", "cycle_id", "results", "column_defs"])
        pagination = data["pagination"]
        results = data["results"]
        column_defs = data["column_defs"]

        self.assertEqual(pagination["total"], 1)
        self.assertEqual(len(results), 1)
        self.assertEqual(list(column_defs[0].keys()), ["field", "headerName"])
        self.assertEqual(list(column_defs[-1].keys()), ["field", "headerName"])

    def test_merged_indicators_provided_on_filter_endpoint(self):
        url = (
            reverse("api:v4:tax_lot_properties-filter")
            + f"?inventory_type=property&cycle_id={self.cycle.pk}&organization_id={self.org.pk}&page=1&per_page=999999999"
        )
        response = self.client.post(url, content_type="application/json")
        data = json.loads(response.content)
        self.assertFalse(data["results"][0]["merged_indicator"])

        url = (
            reverse("api:v4:tax_lot_properties-filter")
            + f"?inventory_type=property&cycle_id={self.cycle.pk}&organization_id={self.org.pk}&page=1&per_page=999999999"
        )
        response = self.client.post(url, content_type="application/json")
        data = json.loads(response.content)
        self.assertTrue(data["results"][0]["merged_indicator"])

        url = (
            reverse("api:v4:tax_lot_properties-filter")
            + f"?inventory_type=property&cycle_id={self.cycle.pk}&organization_id={self.org.pk}&page=1&per_page=999999999"
        )
        response = self.client.post(url, content_type="application/json")
        data = json.loads(response.content)
        related = data["results"][0]["related"][0]
        self.assertTrue("merged_indicator" in related)
        self.assertFalse(related["merged_indicator"])


class PropertyViewTestsPermissions(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()

        # create property with label
        self.profile = ColumnMappingProfile.objects.get(profile_type=ColumnMappingProfile.BUILDINGSYNC_DEFAULT)
        self.cycle = self.cycle_factory.get_cycle()
        self.view = self.property_view_factory.get_property_view(cycle=self.cycle)
        self.taxlot_view = self.taxlot_view_factory.get_taxlot_view(cycle=self.cycle)
        self.property = Property.objects.create(organization=self.org, access_level_instance=self.org.root)
        self.label = StatusLabel.objects.create(
            color="red",
            name="test_label",
            super_organization=self.org,
        )
        self.view.labels.add(self.label)
        self.view.property = self.property
        self.view.save()

    def test_property_filter(self):
        url = (
            reverse("api:v4:tax_lot_properties-filter") + f"?inventory_type=property&cycle_id={self.cycle.pk}&organization_id={self.org.pk}"
        )

        # root member can
        self.login_as_root_member()
        resp = self.client.post(url, content_type="application/json")
        assert resp.status_code == 200
        assert resp.json()["pagination"]["total"] == 1

        # child member cannot
        self.login_as_child_member()
        resp = self.client.post(url, content_type="application/json")
        assert resp.status_code == 200
        assert resp.json()["pagination"]["total"] == 0
