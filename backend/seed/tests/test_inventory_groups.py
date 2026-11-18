"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json

import pytest
from django.db import IntegrityError
from django.urls import reverse_lazy

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import ROLE_VIEWER
from seed.models import InventoryGroup, InventoryGroupMapping, Meter, Property, PropertyView, Scenario, TaxLot
from seed.models.inventory_groups import VIEW_LIST_PROPERTY, VIEW_LIST_TAXLOT
from seed.test_helpers.fake import FakePropertyFactory, FakePropertyViewFactory, FakeSystemFactory
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

        # create 3 properties with 2 meters each. Each meter has 2 readings
        self.view1 = self.property_view_factory.get_property_view()
        self.view2 = self.property_view_factory.get_property_view()
        self.view3 = self.property_view_factory.get_property_view()
        self.cycle2 = self.cycle_factory.get_cycle()
        # create 2nd cycle for properties in 2 cycles

        # add properties to group
        self._put_group_mappings([self.property_group.id], [self.view1.id, self.view2.id], "property")

        # helper functions to create meters and readings
        def create_meter_entry(property_view_id, source_id):
            payload = {"type": "Electric", "source": "Manual Entry", "source_id": source_id, "connection_type": "Imported"}
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
        url = reverse_lazy("api:v3:inventory_groups-list") + f"?organization_id={self.org.id}"
        data = {"name": "test1", "organization": self.org.id, "access_level_instance": self.org.root.id, "inventory_type": "Property"}
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")

        assert response.status_code == 400
        response = response.json()
        assert response == {"non_field_errors": ["The fields name, organization must make a unique set."]}

        data["name"] = "test3"
        response = self.client.post(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 201

        url = reverse_lazy("api:v3:inventory_groups-detail", args=[self.property_group.id]) + f"?organization_id={self.org.id}"
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")

        assert response.status_code == 400
        response = response.json()
        assert response == {"non_field_errors": ["The fields name, organization must make a unique set."]}

    def test_group_mapping_constraints(self):
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

    def test_tax_lot_group_mappings(self):
        taxlot_view = self.taxlot_view_factory.get_taxlot_view()
        response = self._put_group_mappings([self.taxlot_group.id], [taxlot_view.id], "tax_lot")
        assert response.status_code == 200
        assert response.json()["num_updated"] == 1
        assert list(self.taxlot_group.group_mappings.values_list("taxlot_id", flat=True)) == [taxlot_view.taxlot_id]

        url = reverse_lazy("api:v3:inventory_group_mappings-put") + f"?organization_id={self.org.id}"
        data = {
            "inventory_ids": [taxlot_view.id],
            "add_group_ids": [],
            "remove_group_ids": [self.taxlot_group.id],
            "inventory_type": "tax_lot",
        }
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 200
        assert response.json()["num_updated"] == 1
        assert not self.taxlot_group.group_mappings.exists()

    def test_group_mappings_errors(self):
        url = reverse_lazy("api:v3:inventory_group_mappings-put") + f"?organization_id={self.org.id}"
        data = {
            "inventory_ids": [self.view3.id],
            "add_group_ids": [self.property_group.id],
            "remove_group_ids": [self.property_group.id],
            "inventory_type": "property",
        }
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 422
        assert response.json() == {"status": "error", "message": "add_group_ids and remove_group_ids cannot contain elements in common"}
        assert self.property_group.group_mappings.count() == 2

    def test_group_mappings_add_all(self):
        # without inventory_ids, all of the organization's properties not yet in the group are added
        org2, _, _ = create_organization(self.superuser, "org2")
        org2_property = Property.objects.create(organization=org2, access_level_instance=org2.root)

        response = self._put_group_mappings([self.property_group.id], [], "property")
        assert response.status_code == 200
        org_property_ids = set(Property.objects.filter(organization=self.org).values_list("id", flat=True))
        assert response.json()["num_updated"] == len(org_property_ids) - 2
        mapped_property_ids = list(self.property_group.group_mappings.values_list("property_id", flat=True))
        assert sorted(mapped_property_ids) == sorted(org_property_ids)
        assert org2_property.id not in mapped_property_ids

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

        # setup: create 3 properties with 2 meters each. Each meter has 2 readings
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
            payload = {"type": "Electric", "source": "Manual Entry", "source_id": source_id, "connection_type": "Imported"}
            url = reverse_lazy("api:v3:property-meters-list", kwargs={"property_pk": property_view_id}) + f"?organization_id={self.org.id}"
            response = self.client.post(url, data=json.dumps(payload), content_type="application/json")
            return response.json()["id"]

        # create 3 meters
        self.meter1_id = create_meter_entry(view1.id, 101)
        self.meter2_id = create_meter_entry(view2.id, 201)
        self.meter3_id = create_meter_entry(view3.id, 301)

    def test_group_meters(self):
        url = reverse_lazy("api:v3:inventory_group-meters-list", args=[self.property_group.id]) + f"?organization_id={self.org.id}"
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
        assert sorted(data.keys()) == ["column_defs", "readings"]
        # assert 4 columns: start, end, meter 1, meter 2
        assert len(data["column_defs"]) == 4

    def test_group_meters_tax_lot_group(self):
        url = reverse_lazy("api:v3:inventory_group-meters-list", args=[self.taxlot_group.id]) + f"?organization_id={self.org.id}"
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        assert response.json() == {"status": "success", "data": []}

    def test_group_meter_update_meter_not_in_group(self):
        url = (
            reverse_lazy("api:v3:inventory_group-meters-detail", args=[self.property_group.id, self.meter3_id])
            + f"?organization_id={self.org.id}"
        )
        response = self.client.put(url, data=json.dumps({"alias": "new alias"}), content_type="application/json")
        assert response.status_code == 404
        assert Meter.objects.get(pk=self.meter3_id).alias != "new alias"

    def test_group_meter_retrieve_and_destroy_respect_hierarchy(self):
        url = (
            reverse_lazy("api:v3:inventory_group-meters-detail", args=[self.property_group.id, self.meter1_id])
            + f"?organization_id={self.org.id}"
        )

        # the root-level group is outside the child member's access level
        self.login_as_child_member()
        assert self.client.get(url, content_type="application/json").status_code == 404
        assert self.client.delete(url, content_type="application/json").status_code == 404
        assert Meter.objects.filter(pk=self.meter1_id).exists()

        self.login_as_root_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        assert response.json()["data"]["id"] == self.meter1_id
        assert self.client.delete(url, content_type="application/json").status_code == 204
        assert not Meter.objects.filter(pk=self.meter1_id).exists()

    def test_group_meter_create_only_for_group_systems(self):
        system_factory = FakeSystemFactory(organization=self.org)
        group_system = system_factory.get_system(group=self.property_group)
        other_system = system_factory.get_system(group=self.taxlot_group)
        url = reverse_lazy("api:v3:inventory_group-meters-list", args=[self.property_group.id]) + f"?organization_id={self.org.id}"

        payload = {"type": "Electric", "alias": "other", "system_id": other_system.id}
        response = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 404
        assert not Meter.objects.filter(system=other_system).exists()

        payload = {"type": "Electric", "alias": "group", "system_id": group_system.id}
        response = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        assert Meter.objects.filter(system=group_system, alias="group").exists()

    def test_group_meter_create_validates_scenario(self):
        view = PropertyView.objects.filter(property__group_mappings__group=self.property_group).first()
        scenario = Scenario.objects.create(name="group scenario", property_state=view.state)
        org2, _, _ = create_organization(self.superuser, "org2")
        org2_scenario = Scenario.objects.create(
            name="org2 scenario", property_state=FakePropertyViewFactory(organization=org2).get_property_view().state
        )
        url = reverse_lazy("api:v3:inventory_group-meters-list", args=[self.property_group.id]) + f"?organization_id={self.org.id}"

        # scenarios of other organizations can not be assigned
        payload = {"type": "Electric", "alias": "org2 scenario", "property_id": view.property_id, "scenario_id": org2_scenario.id}
        response = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 400
        assert not Meter.objects.filter(alias="org2 scenario").exists()

        payload = {"type": "Electric", "alias": "group scenario", "property_id": view.property_id, "scenario_id": scenario.id}
        response = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        assert response.status_code == 200
        assert Meter.objects.get(alias="group scenario").scenario_id == scenario.id


class InventoryGroupAccessTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.root_group = InventoryGroup.objects.create(
            name="root group", organization=self.org, inventory_type=VIEW_LIST_PROPERTY, access_level_instance=self.org.root
        )
        self.child_group = InventoryGroup.objects.create(
            name="child group", organization=self.org, inventory_type=VIEW_LIST_PROPERTY, access_level_instance=self.child_level_instance
        )

        self.viewer_user_details = {"username": "root_viewer@demo.com", "password": "test_pass"}
        self.viewer_user = User.objects.create_user(**self.viewer_user_details)
        self.org.add_member(self.viewer_user, self.org.root.id, ROLE_VIEWER)

        self.org2, _, _ = create_organization(self.superuser, "org2")
        self.org2_group = InventoryGroup.objects.create(
            name="org2 group", organization=self.org2, inventory_type=VIEW_LIST_PROPERTY, access_level_instance=self.org2.root
        )

    def _detail_url(self, group):
        return reverse_lazy("api:v3:inventory_groups-detail", args=[group.id]) + f"?organization_id={self.org.id}"

    def _group_data(self, name, access_level_instance, organization=None):
        return json.dumps(
            {
                "name": name,
                "organization": (organization or self.org).id,
                "access_level_instance": access_level_instance.id,
                "inventory_type": "Property",
            }
        )

    def test_retrieve_respects_hierarchy(self):
        self.login_as_child_member()
        response = self.client.get(self._detail_url(self.root_group), content_type="application/json")
        assert response.status_code == 404

        response = self.client.get(self._detail_url(self.child_group), content_type="application/json")
        assert response.status_code == 200
        assert response.json()["data"]["id"] == self.child_group.id

        # groups of other organizations are not found
        response = self.client.get(self._detail_url(self.org2_group), content_type="application/json")
        assert response.status_code == 404

    def test_destroy_requires_member_and_respects_hierarchy(self):
        self.client.login(**self.viewer_user_details)
        response = self.client.delete(self._detail_url(self.child_group), content_type="application/json")
        assert response.status_code == 403
        assert InventoryGroup.objects.filter(pk=self.child_group.id).exists()

        self.login_as_child_member()
        response = self.client.delete(self._detail_url(self.root_group), content_type="application/json")
        assert response.status_code == 404
        assert InventoryGroup.objects.filter(pk=self.root_group.id).exists()

        response = self.client.delete(self._detail_url(self.child_group), content_type="application/json")
        assert response.status_code == 204
        assert not InventoryGroup.objects.filter(pk=self.child_group.id).exists()

    def test_create_and_update_respect_hierarchy(self):
        url = reverse_lazy("api:v3:inventory_groups-list") + f"?organization_id={self.org.id}"

        # groups can only be created in the requested organization, even by superusers
        data = self._group_data("org2 new", self.org2.root, organization=self.org2)
        response = self.client.post(url, data=data, content_type="application/json")
        assert response.status_code == 404
        assert not InventoryGroup.objects.filter(name="org2 new").exists()

        self.login_as_child_member()
        response = self.client.post(url, data=self._group_data("root new", self.org.root), content_type="application/json")
        assert response.status_code == 404
        assert not InventoryGroup.objects.filter(name="root new").exists()

        response = self.client.post(url, data=self._group_data("child new", self.child_level_instance), content_type="application/json")
        assert response.status_code == 201
        assert InventoryGroup.objects.get(name="child new").access_level_instance == self.child_level_instance

        # groups can not be moved above the user's access level
        response = self.client.put(
            self._detail_url(self.child_group), data=self._group_data("child renamed", self.org.root), content_type="application/json"
        )
        assert response.status_code == 404
        self.child_group.refresh_from_db()
        assert self.child_group.access_level_instance == self.child_level_instance

        response = self.client.put(
            self._detail_url(self.child_group),
            data=self._group_data("child renamed", self.child_level_instance),
            content_type="application/json",
        )
        assert response.status_code == 200
        self.child_group.refresh_from_db()
        assert self.child_group.name == "child renamed"

        # a group can be updated without renaming it, but not to another group's name
        response = self.client.put(
            self._detail_url(self.child_group),
            data=self._group_data("child renamed", self.child_level_instance),
            content_type="application/json",
        )
        assert response.status_code == 200
        response = self.client.put(
            self._detail_url(self.child_group),
            data=self._group_data("child new", self.child_level_instance),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_group_mappings_respect_hierarchy(self):
        url = reverse_lazy("api:v3:inventory_group_mappings-put") + f"?organization_id={self.org.id}"

        # groups of other organizations can not be modified
        org2_view = FakePropertyViewFactory(organization=self.org2).get_property_view()
        InventoryGroupMapping.objects.create(property=org2_view.property, group=self.org2_group)
        data = {
            "inventory_ids": [org2_view.id],
            "add_group_ids": [],
            "remove_group_ids": [self.org2_group.id],
            "inventory_type": "property",
        }
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 404
        assert self.org2_group.group_mappings.count() == 1

        # groups above the user's access level can not be modified
        root_view = self.property_view_factory.get_property_view()
        InventoryGroupMapping.objects.create(property=root_view.property, group=self.root_group)
        self.login_as_child_member()
        data = {
            "inventory_ids": [root_view.id],
            "add_group_ids": [],
            "remove_group_ids": [self.root_group.id],
            "inventory_type": "property",
        }
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 404
        assert self.root_group.group_mappings.count() == 1

        child_property = self.property_factory.get_property(access_level_instance=self.child_level_instance)
        child_view = self.property_view_factory.get_property_view(prprty=child_property)
        data = {
            "inventory_ids": [child_view.id],
            "add_group_ids": [self.child_group.id],
            "remove_group_ids": [],
            "inventory_type": "property",
        }
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 200
        assert self.child_group.group_mappings.count() == 1
