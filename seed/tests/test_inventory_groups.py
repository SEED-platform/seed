import json
import pytest
from django.db import IntegrityError
from django.urls import reverse_lazy

from seed.models import InventoryGroup, InventoryGroupMapping, Property, TaxLot, AccessLevelInstance
from seed.models.inventory_groups import VIEW_LIST_PROPERTY, VIEW_LIST_TAXLOT
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.organizations import create_organization


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
        url = reverse_lazy('api:v3:inventory_groups-list')
        data = {
            "name": "test1",
            "organization": self.org.id,
            "access_level_instance": self.org.root.id,
            "inventory_type": "Property"
        }
        result = self.client.post(url, data=json.dumps(data), content_type="application/json")
        assert result.status_code == 400
        result = result.json()
        assert result == {'status': 'error', 'message': {'non_field_errors': ['Inventory Group Name must be unique.']}}

        data["name"] = 'test3'
        result = self.client.post(url, data=json.dumps(data), content_type="application/json")
        assert result.status_code == 201

        url = reverse_lazy('api:v3:inventory_groups-detail', args=[self.property_group.id])
        result = self.client.put(url, data=json.dumps(data), content_type="application/json")
        assert result.status_code == 400 
        result = result.json()
        assert result == {'status': 'error', 'message': {'non_field_errors': ['Inventory Group Name must be unique.']}}
