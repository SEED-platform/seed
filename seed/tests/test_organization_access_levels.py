# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
import os
import time

from django.urls import reverse_lazy

from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.models import Organization, TaxLot
from seed.tests.util import AccessLevelBaseTestCase


class TestOrganizationViews(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()

    def test_access_level_tree(self):
        url = reverse_lazy(
            "api:v3:organization-access_levels-tree",
            args=[self.org.id],
        )
        sibling = self.org.add_new_access_level_instance(self.org.root.id, "sibling")
        child_dict = {
            "id": self.child_level_instance.pk,
            "data": {
                "name": "child",
                "organization": self.org.id,
                "path": {"root": "root", "child": "child"},
            },
        }
        sibling_dict = {
            "id": sibling.pk,
            "data": {
                "name": "sibling",
                "organization": self.org.id,
                "path": {"root": "root", "child": "sibling"},
            },
        }

        root_dict = {
            "id": self.org.root.pk,
            "data": {
                "name": self.root_level_instance.name,
                "organization": self.org.id,
                "path": {"root": "root"},
            },
        }

        # get tree
        self.login_as_root_member()
        raw_result = self.client.get(url)
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
                    "data": {
                        "name": self.root_level_instance.name,
                        "organization": self.org.id,
                        "path": {"root": "root"},
                    },
                    "children": [
                        {
                            "id": aunt.pk,
                            "data": {
                                "name": "aunt",
                                "organization": self.org.id,
                                "path": {"root": "root", "child": "aunt"},
                            },
                        },
                        {
                            "id": self.child_level_instance.pk,
                            "data": {
                                "name": "child",
                                "organization": self.org.id,
                                "path": {"root": "root", "child": "child"},
                            },
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
