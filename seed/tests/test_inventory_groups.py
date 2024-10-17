import json

import pytest
from django.db import IntegrityError
from django.urls import reverse_lazy

from seed.models import InventoryGroup, InventoryGroupMapping, Property, TaxLot
from seed.models.inventory_groups import VIEW_LIST_PROPERTY, VIEW_LIST_TAXLOT
from seed.test_helpers.fake import FakePropertyFactory, FakePropertyViewFactory
from seed.tests.util import AccessLevelBaseTestCase


class PropertyViewTestsPermissions(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()

        self.property = Property.objects.create(organization=self.org, access_level_instance=self.org.root)
        self.taxlot = TaxLot.objects.create(organization=self.org, access_level_instance=self.org.root)
        self.property_group = InventoryGroup.objects.create(
            name="test1", organization=self.org, inventory_type=VIEW_LIST_PROPERTY, access_level_instance=self.org.root
        )
        self.taxlot_group = InventoryGroup.objects.create(
            name="test2", organization=self.org, inventory_type=VIEW_LIST_TAXLOT, access_level_instance=self.org.root
        )

    def test_create_good_mapping(self):
        InventoryGroupMapping.objects.create(property=self.property, group=self.property_group)
        InventoryGroupMapping.objects.create(taxlot=self.taxlot, group=self.taxlot_group)

    def test_create_bad_mapping_no_inventory_type(self):
        with pytest.raises(IntegrityError):
            InventoryGroupMapping.objects.create(group=self.property_group)

    def test_create_bad_mapping_two_inventory_type(self):
        with pytest.raises(IntegrityError):
            InventoryGroupMapping.objects.create(property=self.property, taxlot=self.taxlot, group=self.property_group)

    def test_create_bad_mapping_wrong_inventory_type(self):
        with pytest.raises(IntegrityError):
            InventoryGroupMapping.objects.create(property=self.property, group=self.taxlot_group)
        with pytest.raises(IntegrityError):
            InventoryGroupMapping.objects.create(taxlot=self.taxlot, group=self.property_group)

    def test_create_bad_mapping_bad_ali(self):
        self.property_group.access_level_instance = self.child_level_instance
        self.property_group.save()

        with pytest.raises(IntegrityError):
            InventoryGroupMapping.objects.create(property=self.property, group=self.property_group)

    def test_group_constraints(self):
        url = reverse_lazy("api:v3:inventory_groups-list")
        data = {"name": "test1", "organization": self.org.id, "access_level_instance": self.org.root.id, "inventory_type": "Property"}
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 400
        response = response.json()
        assert response == {"status": "error", "message": {"non_field_errors": ["Inventory Group Name must be unique."]}}

        data["name"] = "test3"
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 201

        url = reverse_lazy("api:v3:inventory_groups-detail", args=[self.property_group.id])
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")

        assert response.status_code == 400
        response = response.json()
        assert response == {"status": "error", "message": {"non_field_errors": ["Inventory Group Name must be unique."]}}

    def test_group_mapping_contraints(self):
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.view_factory = FakePropertyViewFactory(organization=self.org)

        self.p1a = self.property_factory.get_property(access_level_instance=self.org.root)
        self.p1b = self.property_factory.get_property(access_level_instance=self.org.root)
        self.p2a = self.property_factory.get_property(access_level_instance=self.child_level_instance)

        self.view1a = self.view_factory.get_property_view(prprty=self.p1a)
        self.view1b = self.view_factory.get_property_view(prprty=self.p1b)
        self.view2a = self.view_factory.get_property_view(prprty=self.p2a)

        url = reverse_lazy("api:v3:inventory_group_mappings-put") + f"?organization_id={self.org.id}"
        data = {
            "inventory_ids": [self.view1a.id, self.view1b.id, self.view2a.id],
            "add_group_ids": [self.property_group.id],
            "remove_group_ids": [],
            "inventory_type": "property",
        }

        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 400
        assert response.json()["message"] == "Access Level mismatch between group and inventory."

        data["inventory_ids"] = [self.view1a.id]
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 200

    def test_group_meters(self):
        # setup: create 3 properties with 2 meters each. Each mmeter has 2 readings
        view1 = self.property_view_factory.get_property_view()
        view2 = self.property_view_factory.get_property_view()
        view3 = self.property_view_factory.get_property_view()

        # add properties to group
        url = reverse_lazy("api:v3:inventory_group_mappings-put") + f"?organization_id={self.org.id}"
        data = {
            "inventory_ids": [view1.id, view2.id],
            "add_group_ids": [self.property_group.id],
            "remove_group_ids": [],
            "inventory_type": "property",
        }
        self.client.put(url, data=json.dumps(data), content_type="application/json")

        # helper functions to create meters and readings
        def create_meter_entry(property_view_id, source_id):
            payload = {"type": "Electric", "source": "Manual Entry", "source_id": source_id, "connection_type": "From Outside"}
            url = reverse_lazy("api:v3:property-meters-list", kwargs={"property_pk": property_view_id}) + f"?organization_id={self.org.id}"
            response = self.client.post(url, data=json.dumps(payload), content_type="application/json")
            return response.json()["id"]

        # create 3 meters
        meter1_id = create_meter_entry(view1.id, 101)
        meter2_id = create_meter_entry(view2.id, 201)
        create_meter_entry(view3.id, 301)

        url = reverse_lazy("api:v3:inventory_groups-meters", args=[self.property_group.id]) + f"?organization_id={self.org.id}"
        response = self.client.get(url, content_type="application/json")
        data = response.json()["data"]
        assert len(data) == 2
        assert data[0]["id"] == meter1_id
        assert data[1]["id"] == meter2_id


class GroupMeterTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()

        self.property = Property.objects.create(organization=self.org, access_level_instance=self.org.root)
        self.taxlot = TaxLot.objects.create(organization=self.org, access_level_instance=self.org.root)
        self.property_group = InventoryGroup.objects.create(
            name="test1", organization=self.org, inventory_type=VIEW_LIST_PROPERTY, access_level_instance=self.org.root
        )
        self.taxlot_group = InventoryGroup.objects.create(
            name="test2", organization=self.org, inventory_type=VIEW_LIST_TAXLOT, access_level_instance=self.org.root
        )

        # setup: create 3 properties with 2 meters each. Each mmeter has 2 readings
        view1 = self.property_view_factory.get_property_view()
        view2 = self.property_view_factory.get_property_view()
        view3 = self.property_view_factory.get_property_view()

        # add properties to group
        url = reverse_lazy("api:v3:inventory_group_mappings-put") + f"?organization_id={self.org.id}"
        data = {
            "inventory_ids": [view1.id, view2.id],
            "add_group_ids": [self.property_group.id],
            "remove_group_ids": [],
            "inventory_type": "property",
        }
        self.client.put(url, data=json.dumps(data), content_type="application/json")

        # helper functions to create meters and readings
        def create_meter_entry(property_view_id, source_id):
            payload = {"type": "Electric", "source": "Manual Entry", "source_id": source_id, "connection_type": "From Outside"}
            url = reverse_lazy("api:v3:property-meters-list", kwargs={"property_pk": property_view_id}) + f"?organization_id={self.org.id}"
            response = self.client.post(url, data=json.dumps(payload), content_type="application/json")
            return response.json()["id"]

        # create 3 meters
        self.meter1_id = create_meter_entry(view1.id, 101)
        self.meter2_id = create_meter_entry(view2.id, 201)
        self.meter3_id = create_meter_entry(view3.id, 301)

    def test_group_meters(self):
        url = reverse_lazy("api:v3:inventory_groups-meters", args=[self.property_group.id]) + f"?organization_id={self.org.id}"
        response = self.client.get(url, content_type="application/json")

        data = response.json()["data"]
        assert len(data) == 2
        assert data[0]["id"] == self.meter1_id
        assert data[1]["id"] == self.meter2_id

    def test_group_meter_usage(self):
        url = reverse_lazy("api:v3:inventory_groups-meter-usage", args=[self.property_group.id]) + f"?organization_id={self.org.id}"
        data = {"interval": "Exact"}
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")
        data = response.json()
        assert data["status"] == "success"
        data = data["data"]
        assert list(data.keys()) == ["column_defs", "readings"]
        # assert 4 columns: start, end, meter 1, meter 2
        assert len(data["column_defs"]) == 4
