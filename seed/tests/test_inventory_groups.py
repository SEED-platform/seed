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


class InventoryGroupViewTests(AccessLevelBaseTestCase):
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

        # create 3 properties with 2 meters each. Each mmeter has 2 readings
        self.view1 = self.property_view_factory.get_property_view()
        self.view2 = self.property_view_factory.get_property_view()
        self.view3 = self.property_view_factory.get_property_view()
        self.cycle2 = self.cycle_factory.get_cycle()
        # create 2nd cycle for properties in 2 cycles

        # add properties to group
        self._put_group_mappings([self.property_group.id], [self.view1.id, self.view2.id], "property")

        # helper functions to create meters and readings
        def create_meter_entry(property_view_id, source_id):
            payload = {"type": "Electric", "source": "Manual Entry", "source_id": source_id, "connection_type": "From Outside"}
            url = reverse_lazy("api:v3:property-meters-list", kwargs={"property_pk": property_view_id}) + f"?organization_id={self.org.id}"
            response = self.client.post(url, data=json.dumps(payload), content_type="application/json")
            return response.json()["id"]

        # create 3 meters
        self.meter1_id = create_meter_entry(self.view1.id, 101)
        self.meter2_id = create_meter_entry(self.view2.id, 201)
        self.meter3_id = create_meter_entry(self.view3.id, 301)

    def _put_group_mappings(self, group_ids, view_ids, inventory_type):
        url = reverse_lazy("api:v3:inventory_group_mappings-put") + f"?organization_id={self.org.id}"
        data = {
            "inventory_ids": view_ids,
            "add_group_ids": group_ids,
            "remove_group_ids": [],
            "inventory_type": inventory_type,
        }
        return self.client.put(url, data=json.dumps(data), content_type="application/json")

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

        response = self._put_group_mappings([self.property_group.id], [self.view1a.id, self.view1b.id, self.view2a.id], "property")
        assert response.status_code == 400
        assert response.json()["message"] == "Access Level mismatch between group and inventory."

        response = self._put_group_mappings([self.property_group.id], [self.view1a.id], "property")
        assert response.status_code == 200

    def test_merge_group_duplicates(self):
        view = self.property_view_factory.get_property_view()
        self._put_group_mappings([self.property_group.id], [view.id], "property")

        # Merge the properties
        url = reverse_lazy("api:v3:properties-merge") + f"?organization_id={self.org.pk}"
        data = {"property_view_ids": [self.view1.pk, view.pk]}
        self.client.post(url, data=json.dumps(data), content_type="application/json")

        new_property = Property.objects.last()
        assert new_property.group_mappings.count() == 1

    def test_merge_group_order(self):
        view4 = self.property_view_factory.get_property_view()
        view5 = self.property_view_factory.get_property_view()
        url = reverse_lazy("api:v3:properties-merge") + f"?organization_id={self.org.pk}"

        # test group history preserved if first view has groups, second has none
        data = {"property_view_ids": [self.view1.pk, view4.pk]}
        self.client.post(url, data=json.dumps(data), content_type="application/json")

        new_property = Property.objects.last()
        assert new_property.group_mappings.count() == 1

        # test group history preserved if second has groups, first has none
        data = {"property_view_ids": [view5.pk, self.view1.pk]}
        self.client.post(url, data=json.dumps(data), content_type="application/json")

        new_property = Property.objects.last()
        assert new_property.group_mappings.count() == 1

    def test_clean_group(self):
        assert self.property_group.group_mappings.count() == 2
        view4 = self.property_view_factory.get_property_view()
        view5 = self.property_view_factory.get_property_view()
        # add a view with a shared property to a different cycle
        self.property_view_factory.get_property_view(prprty=view4.property, cycle=self.cycle2)
        # add properties to groups
        self._put_group_mappings([self.property_group.id], [view4.id, view5.id], "property")
        assert self.property_group.group_mappings.count() == 4

        # bulk delete views
        url = reverse_lazy("api:v3:properties-batch-delete") + f"?organization_id={self.org.pk}"
        params = json.dumps({"property_view_ids": [view4.id, view5.id]})
        self.client.delete(url, params, content_type="application/json")

        # only view5 mapping should be removed as view4a exists in cycle2
        assert self.property_group.group_mappings.count() == 3


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
