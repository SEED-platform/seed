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

class GroupAccessLevels(AccessLevelBaseTestCase):
    def test_return_group_common_ali(self):
        """
        find the lowest common ALI in a group. 

        ALI Tree:
                          root
                        /      \
                     child     sibling
                    /    \
        grandchild a     grandchild b
        """
        self.org.access_level_names = ["1st Gen", "2nd Gen", "3rd Gen"]
        self.sibling_level_instance = self.org.add_new_access_level_instance(self.org.root.id, "sibling")
        self.child_a_level_instance = self.org.add_new_access_level_instance(self.child_level_instance.id, "grandchild a")
        self.child_b_level_instance = self.org.add_new_access_level_instance(self.child_level_instance.id, "grandchild b")

        self.p1 = Property.objects.create(organization=self.org, access_level_instance=self.org.root)
        self.p2 = Property.objects.create(organization=self.org, access_level_instance=self.child_level_instance)
        self.p3 = Property.objects.create(organization=self.org, access_level_instance=self.sibling_level_instance)
        self.p4 = Property.objects.create(organization=self.org, access_level_instance=self.child_a_level_instance)
        self.p5 = Property.objects.create(organization=self.org, access_level_instance=self.child_b_level_instance)

        # all properties across all groups. Least common ancestor is root
        self.group1 = InventoryGroup.objects.create(
            organization=self.org, name="test1", inventory_type=VIEW_LIST_PROPERTY, access_level_instance=self.org.root
        )
        # least common ancestor is child
        self.group2 = InventoryGroup.objects.create(
            organization=self.org, name="test1", inventory_type=VIEW_LIST_PROPERTY, access_level_instance=self.org.root
        )

        InventoryGroupMapping.objects.bulk_create([InventoryGroupMapping(property=prop, group=self.group1) for prop in [self.p1, self.p2, self.p3, self.p4, self.p5]])
        InventoryGroupMapping.objects.bulk_create([InventoryGroupMapping(property=prop, group=self.group2) for prop in [self.p2, self.p4, self.p5]])

        lca1 = self.group1.lowest_common_ancestor()
        lca2 = self.group2.lowest_common_ancestor()
        assert self.org.root == lca1
        assert self.child_level_instance == lca2

