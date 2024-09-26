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
