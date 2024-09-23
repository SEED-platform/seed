import pytest
from django.db import IntegrityError

from seed.models import InventoryGroup, InventoryGroupMapping, Property, TaxLot, AccessLevelInstance
from seed.models.inventory_groups import VIEW_LIST_PROPERTY, VIEW_LIST_TAXLOT
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
