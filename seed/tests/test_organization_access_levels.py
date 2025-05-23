"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
import os
import time

from django.urls import reverse_lazy

from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.models import Organization, Property, TaxLot
from seed.test_helpers.fake import FakePropertyFactory, FakePropertyViewFactory
from seed.tests.util import AccessLevelBaseTestCase


class TestOrganizationViews(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)

    def test_access_level_tree(self):
        url = reverse_lazy(
            "api:v3:organization-access_levels-tree",
            args=[self.org.id],
        )
        url_descendant = reverse_lazy("api:v3:organization-access_levels-descendant-tree", args=[self.org.id])
        sibling = self.org.add_new_access_level_instance(self.org.root.id, "sibling")
        child_dict = {
            "id": self.child_level_instance.pk,
            "name": "child",
            "organization": self.org.id,
            "path": {"root": "root", "child": "child"},
        }
        sibling_dict = {
            "id": sibling.pk,
            "name": "sibling",
            "organization": self.org.id,
            "path": {"root": "root", "child": "sibling"},
        }

        root_dict = {
            "id": self.org.root.pk,
            "name": self.root_level_instance.name,
            "organization": self.org.id,
            "path": {"root": "root"},
        }

        # get tree & descendant tree
        self.login_as_root_member()
        raw_result = self.client.get(url)
        result = json.loads(raw_result.content)
        assert result == {
            "access_level_names": ["root", "child"],
            "access_level_tree": [{**root_dict, "children": [child_dict, sibling_dict]}],
        }
        raw_result = self.client.get(url_descendant)
        result = json.loads(raw_result.content)
        assert result == {
            "access_level_names": ["root", "child"],
            "access_level_tree": [{**root_dict, "children": [child_dict, sibling_dict]}],
        }

        self.login_as_child_member()
        raw_result = self.client.get(url)
        result = json.loads(raw_result.content)
        assert result == {
            "access_level_names": ["root", "child"],
            "access_level_tree": [{**root_dict, "children": [child_dict]}],
        }
        raw_result = self.client.get(url_descendant)
        result = json.loads(raw_result.content)
        assert result == {
            "access_level_names": ["child"],
            "access_level_tree": [child_dict],
        }

    def test_edit_access_level_names(self):
        # get default access_level_names
        url = reverse_lazy("api:v3:organization-access_levels-tree", args=[self.org.id])
        raw_result = self.client.get(url)
        result = json.loads(raw_result.content)
        assert result["access_level_names"] == ["root", "child"]

        # get update access level names
        url = reverse_lazy("api:v3:organization-access_levels-access-level-names", args=[self.org.id])
        raw_result = self.client.post(
            url,
            data=json.dumps({"access_level_names": ["new name", "boo"]}),
            content_type="application/json",
        )
        result = json.loads(raw_result.content)
        assert result == ["new name", "boo"]

        assert Organization.objects.get(pk=self.org.id).access_level_names == ["new name", "boo"]

    def test_edit_access_level_names_column_names(self):
        # get update access level names
        url = reverse_lazy("api:v3:organization-access_levels-access-level-names", args=[self.org.id])
        raw_result = self.client.post(
            url,
            data=json.dumps({"access_level_names": ["Address Line 1", "boo"]}),
            content_type="application/json",
        )
        assert raw_result.status_code == 400

    def test_edit_access_level_names_delete_root(self):
        # get try to clear access_level_names
        url = reverse_lazy("api:v3:organization-access_levels-access-level-names", args=[self.org.id])
        raw_result = self.client.post(
            url,
            data=json.dumps({"access_level_names": []}),
            content_type="application/json",
        )
        assert raw_result.status_code == 400

    def test_edit_access_level_names_delete_level(self):
        # get try to add too few levels
        url = reverse_lazy("api:v3:organization-access_levels-access-level-names", args=[self.org.id])
        raw_result = self.client.post(
            url,
            data=json.dumps({"access_level_names": ["just one"]}),
            content_type="application/json",
        )

        assert raw_result.status_code == 200
        assert AccessLevelInstance.objects.count() == 1
        assert AccessLevelInstance.objects.first().name == "root"

    def test_edit_access_level_names_duplicates(self):
        url = reverse_lazy("api:v3:organization-access_levels-access-level-names", args=[self.org.id])
        raw_result = self.client.post(
            url,
            data=json.dumps({"access_level_names": ["hip", "hip"]}),
            content_type="application/json",
        )
        assert raw_result.status_code == 400

    def test_edit_access_level_names_column_name_collision(self):
        url = reverse_lazy("api:v3:organization-access_levels-access-level-names", args=[self.org.id])
        raw_result = self.client.post(
            url,
            data=json.dumps({"access_level_names": ["Address Line 1"]}),
            content_type="application/json",
        )
        assert raw_result.status_code == 400

    def test_add_new_access_level_instance(self):
        url = reverse_lazy("api:v3:organization-access_levels-add-instance", args=[self.org.id])
        raw_result = self.client.post(
            url,
            data=json.dumps({"parent_id": self.org.root.pk, "name": "aunt"}),
            content_type="application/json",
        )
        assert raw_result.status_code == 201

        # get new access_level_instance
        aunt = AccessLevelInstance.objects.get(organization=self.org, name="aunt")

        # check result
        result = json.loads(raw_result.content)
        assert result == {
            "access_level_names": ["root", "child"],
            "access_level_tree": [
                {
                    "id": self.org.root.pk,
                    "name": self.root_level_instance.name,
                    "organization": self.org.id,
                    "path": {"root": "root"},
                    "children": [
                        {
                            "id": aunt.pk,
                            "name": "aunt",
                            "organization": self.org.id,
                            "path": {"root": "root", "child": "aunt"},
                        },
                        {
                            "id": self.child_level_instance.pk,
                            "name": "child",
                            "organization": self.org.id,
                            "path": {"root": "root", "child": "child"},
                        },
                    ],
                }
            ],
        }

    def test_add_alis_from_file_bad1(self):
        """This test makes sure that import files will fail when incorrect
        access level names (headers) are provided"""
        self.org.access_level_names = ["top level", "Sector", "Sub Sector", "Partner"]
        self.org.save()

        filename = "access-levels-wrong1.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        uploaded_filepath = filepath
        url = reverse_lazy("api:v3:organization-access_levels-start-save-data", args=[self.org.id])
        raw_result = self.client.post(url, data=json.dumps({"filename": uploaded_filepath}), content_type="application/json")
        # 200 - process ok
        assert raw_result.status_code == 200
        result = json.loads(raw_result.content)
        assert result["message"] == "Invalid Column Name: \"'partner'\""
        assert result["status"] == "error"

    def test_add_alis_from_file_bad2(self):
        """This test makes sure that import files will fail when additional
        access level columns that do not exist in the hierarchy are provided"""
        self.org.access_level_names = ["top level", "Sector", "Sub Sector", "Partner"]
        self.org.save()

        filename = "access-levels-wrong2.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        uploaded_filepath = filepath
        url = reverse_lazy("api:v3:organization-access_levels-start-save-data", args=[self.org.id])
        raw_result = self.client.post(url, data=json.dumps({"filename": uploaded_filepath}), content_type="application/json")
        # 200 - process finishes without crashing
        assert raw_result.status_code == 200
        result = json.loads(raw_result.content)
        assert result["message"] == {
            "Test Partner 1": {
                "message": "Error reading CSV data row: {'sector': 'Test', 'sub sector': 'Sub Test', 'partner': 'Test Partner 1', 'extra': 'wrong'}...no access level for column extra found"
            }
        }

    def test_add_alis_from_file_bad3(self):
        """This test makes sure that import files will fail when the file
        is incorrectly filled out (no data in col 1 but data in col 2, etc.)"""

        self.org.access_level_names = ["top level", "Sector", "Sub Sector", "Partner"]
        self.org.save()

        filename = "access-levels-wrong3.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        uploaded_filepath = filepath
        url = reverse_lazy("api:v3:organization-access_levels-start-save-data", args=[self.org.id])
        raw_result = self.client.post(url, data=json.dumps({"filename": uploaded_filepath}), content_type="application/json")
        # 200 - process finishes without crashing
        assert raw_result.status_code == 200
        result = json.loads(raw_result.content)
        assert result["message"] == {
            "Test3 Partner2": {
                "message": "Blank value for column sector in CSV data row: {'sector': '', 'sub sector': 'Test3Sub2', 'partner': 'Test3 Partner2'}...skipping"
            },
            "Test3 Partner3": {
                "message": "Blank value for column sector in CSV data row: {'sector': '', 'sub sector': '', 'partner': 'Test3 Partner3'}...skipping"
            },
        }

    def test_add_access_level_instances_from_file(self):
        self.org.access_level_names = ["top level", "Sector", "Sub Sector", "Partner"]
        self.org.save()

        self.child_level_instance.delete()

        filename = "access-level-instances.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        uploaded_filepath = filepath
        url = reverse_lazy("api:v3:organization-access_levels-start-save-data", args=[self.org.id])
        raw_result = self.client.post(url, data=json.dumps({"filename": uploaded_filepath}), content_type="application/json")

        assert raw_result.status_code == 200

        # todo: deal with the progress loop
        # instead of dealing with the progress loop, just wait a bit
        time.sleep(20)

        # spot check the tree now
        url = reverse_lazy(
            "api:v3:organization-access_levels-tree",
            args=[self.org.id],
        )

        # get tree
        raw_result = self.client.get(url)
        result = json.loads(raw_result.content)
        assert result["access_level_tree"][0]["id"] == self.org.root.pk
        assert len(result["access_level_tree"][0]["children"]) == 8
        assert len(result["access_level_tree"][0]["children"][0]["children"][0]["children"]) == 8

        # retrieve the last access level instance
        _ = AccessLevelInstance.objects.get(organization=self.org, name="Company H")

    def test_can_delete_instance(self):
        self.org.access_level_names += ["2nd gen", "3rd gen"]
        ali = self.org.add_new_access_level_instance(self.org.root.pk, "child")

        url = reverse_lazy(
            "api:v3:organization-access_levels-can-delete-instance",
            args=[self.org.id, ali.pk],
        )
        result = self.client.get(url)
        assert result.json()["can_delete"]

    def test_can_delete_instance_has_relation(self):
        self.org.access_level_names += ["2nd gen", "3rd gen"]
        ali = self.org.add_new_access_level_instance(self.org.root.pk, "child")

        self.taxlot = TaxLot.objects.create(organization=self.org, access_level_instance=ali)

        url = reverse_lazy(
            "api:v3:organization-access_levels-can-delete-instance",
            args=[self.org.id, ali.pk],
        )
        result = self.client.get(url)
        assert not result.json()["can_delete"]
        assert result.json()["reasons"] == ["Has 1 related Taxlot"]

    def test_can_delete_instance_child_has_relation(self):
        self.org.access_level_names += ["2nd gen", "3rd gen"]
        ali = self.org.add_new_access_level_instance(self.org.root.pk, "me")
        child = self.org.add_new_access_level_instance(ali.pk, "child")

        self.taxlot = TaxLot.objects.create(organization=self.org, access_level_instance=child)

        url = reverse_lazy(
            "api:v3:organization-access_levels-can-delete-instance",
            args=[self.org.id, ali.pk],
        )
        result = self.client.get(url)
        assert not result.json()["can_delete"]
        assert result.json()["reasons"] == ["Has 1 related Taxlot"]

    def test_delete_instance(self):
        self.org.access_level_names += ["2nd gen", "3rd gen"]

        self.taxlot = TaxLot.objects.create(organization=self.org, access_level_instance=self.child_level_instance)

        url = reverse_lazy(
            "api:v3:organization-access_levels-delete-instance",
            args=[self.org.id, self.child_level_instance.pk],
        )
        result = self.client.delete(url)

        assert result.status_code == 204
        assert AccessLevelInstance.objects.count() == 1
        assert TaxLot.objects.count() == 0

    def test_delete_instance_root(self):
        url = reverse_lazy(
            "api:v3:organization-access_levels-delete-instance",
            args=[self.org.id, self.org.root.pk],
        )
        result = self.client.delete(url)

        assert result.status_code == 400

    def test_lowest_common_ancestor(self):
        """
        find the lowest common ALI in a group.

        ALI Tree:
                          root
                        /      \
                     child     sibling
                    /    \
        grandchild a     grandchild b
        """
        self.org.access_level_names += ["grand_child"]

        self.sibling_level_instance = self.org.add_new_access_level_instance(self.org.root.id, "sibling")
        self.grand_child_a_level_instance = self.org.add_new_access_level_instance(self.child_level_instance.id, "grandchild a")
        self.grand_child_b_level_instance = self.org.add_new_access_level_instance(self.child_level_instance.id, "grandchild b")
        self.org.save()

        self.p1 = Property.objects.create(organization=self.org, access_level_instance=self.org.root)
        self.p2 = Property.objects.create(organization=self.org, access_level_instance=self.child_level_instance)
        self.p3 = Property.objects.create(organization=self.org, access_level_instance=self.sibling_level_instance)
        self.p4 = Property.objects.create(organization=self.org, access_level_instance=self.grand_child_a_level_instance)
        self.p5 = Property.objects.create(organization=self.org, access_level_instance=self.grand_child_b_level_instance)

        url = reverse_lazy(
            "api:v3:organization-access_levels-lowest-common-ancestor",
            args=[self.org.id],
        )
        data = {"inventory_type": "property", "inventory_ids": [self.p1.id, self.p2.id, self.p3.id, self.p4.id, self.p5.id]}

        result = self.client.post(url, data=json.dumps(data), content_type="application/json")
        result = result.json()["data"]
        assert self.org.root.id == result["id"]
        assert self.org.root.name == result["name"]

        data["inventory_ids"] = [self.p2.id, self.p4.id, self.p5.id]
        result = self.client.post(url, data=json.dumps(data), content_type="application/json")
        result = result.json()["data"]
        assert self.child_level_instance.id == result["id"]
        assert self.child_level_instance.name == result["name"]

        data["inventory_ids"] = [self.p5.id]
        result = self.client.post(url, data=json.dumps(data), content_type="application/json")
        result = result.json()["data"]
        assert self.grand_child_b_level_instance.id == result["id"]
        assert self.grand_child_b_level_instance.name == result["name"]

    def test_ali_filter_by_views(self):
        self.sibling_level_instance = self.org.add_new_access_level_instance(self.org.root.id, "sibling")
        self.org.save()

        p2a = self.property_factory.get_property(organization=self.org, access_level_instance=self.child_level_instance)
        p2b = self.property_factory.get_property(organization=self.org, access_level_instance=self.child_level_instance)
        p3a = self.property_factory.get_property(organization=self.org, access_level_instance=self.sibling_level_instance)
        p3b = self.property_factory.get_property(organization=self.org, access_level_instance=self.sibling_level_instance)

        self.v1a = self.property_view_factory.get_property_view()
        self.v1b = self.property_view_factory.get_property_view()
        self.v2a = self.property_view_factory.get_property_view(prprty=p2a)
        self.v2b = self.property_view_factory.get_property_view(prprty=p2b)
        self.v3a = self.property_view_factory.get_property_view(prprty=p3a)
        self.v3b = self.property_view_factory.get_property_view(prprty=p3b)

        url = reverse_lazy(
            "api:v3:organization-access_levels-filter-by-views",
            args=[self.org.id],
        )
        data = {
            "inventory_type": "property",
            "view_ids": [self.v1a.id, self.v1b.id, self.v2a.id, self.v2b.id, self.v3a.id, self.v3b.id],
        }
        result = self.client.post(url, data=json.dumps(data), content_type="application/json")
        alis = result.json()["access_level_instance_ids"]
        assert len(alis) == 3

        data["view_ids"] = [self.v2a.id, self.v2b.id, self.v3a.id, self.v3b.id]
        result = self.client.post(url, data=json.dumps(data), content_type="application/json")
        alis = result.json()["access_level_instance_ids"]
        assert len(alis) == 2

        data["view_ids"] = [self.v3a.id, self.v3b.id]
        result = self.client.post(url, data=json.dumps(data), content_type="application/json")
        alis = result.json()["access_level_instance_ids"]
        assert len(alis) == 1
        assert alis == [self.sibling_level_instance.id]
