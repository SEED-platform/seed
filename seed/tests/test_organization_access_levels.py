# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json
import os
import time

from django.urls import reverse_lazy

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.models import Organization
from seed.tests.util import DataMappingBaseTestCase
from seed.utils.organizations import create_organization


class TestOrganizationViews(DataMappingBaseTestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details
        )
        self.org, _, _ = create_organization(user, "my org")
        self.org.save()

        self.client.login(**user_details)

    def test_access_level_tree(self):
        url = reverse_lazy('api:v3:organization-access_levels-tree', args=[self.org.id],)

        # get tree
        raw_result = self.client.get(url)
        result = json.loads(raw_result.content)
        assert result == {
            'access_level_names': ['my org'],
            'access_level_tree': [{
                'id': self.org.root.pk,
                'data': {
                    'name': 'root',
                    'organization': self.org.id,
                    'path': {'my org': 'root'},
                }
            },],
        }

        # populate tree
        self.org.access_level_names += ["2nd gen", "3rd gen"]
        self.org.save()
        aunt = self.org.add_new_access_level_instance(self.org.root.id, "aunt")
        mom = self.org.add_new_access_level_instance(self.org.root.id, "mom")
        me = self.org.add_new_access_level_instance(mom.id, "me")

        # get tree
        raw_result = self.client.get(url)
        result = json.loads(raw_result.content)
        assert result == {
            'access_level_names': ['my org', "2nd gen", "3rd gen"],
            'access_level_tree': [{
                'id': self.org.root.pk,
                'data': {
                    'name': 'root',
                    'organization': self.org.id,
                    'path': {'my org': 'root'},
                },
                'children': [
                    {
                        'id': aunt.pk,
                        'data': {
                            'name': 'aunt',
                            'organization': self.org.id,
                            'path': {'my org': 'root', '2nd gen': 'aunt'},
                        }
                    },
                    {
                        'id': mom.pk,
                        'data': {
                            'name': 'mom',
                            'organization': self.org.id,
                            'path': {'my org': 'root', '2nd gen': 'mom'},
                        },
                        'children': [{
                            'id': me.pk,
                            'data': {
                                'name': 'me',
                                'organization': self.org.id,
                                'path': {'my org': 'root', '2nd gen': 'mom', '3rd gen': 'me'},
                            }
                        }]
                    }
                ]
            }],
        }

    def test_edit_access_level_names(self):
        # get default access_level_names
        url = reverse_lazy('api:v3:organization-access_levels-tree', args=[self.org.id])
        raw_result = self.client.get(url)
        result = json.loads(raw_result.content)
        assert result["access_level_names"] == ["my org"]

        # get update access level names
        url = reverse_lazy('api:v3:organization-access_levels-access-level-names', args=[self.org.id])
        raw_result = self.client.post(
            url,
            data=json.dumps({"access_level_names": ["new name", "boo"]}),
            content_type='application/json',
        )
        result = json.loads(raw_result.content)
        assert result == ["new name", "boo"]

        assert Organization.objects.get(pk=self.org.id).access_level_names == ["new name", "boo"]

    def test_edit_access_level_names_too_few(self):
        # get try to clear access_level_names
        url = reverse_lazy('api:v3:organization-access_levels-access-level-names', args=[self.org.id])
        raw_result = self.client.post(
            url,
            data=json.dumps({"access_level_names": []}),
            content_type='application/json',
        )
        assert raw_result.status_code == 400

        # populate tree
        self.org.access_level_names += ["2nd gen", "3rd gen"]
        self.org.save()
        self.org.add_new_access_level_instance(self.org.root.id, "aunt")

        # get try to add too few levels
        url = reverse_lazy('api:v3:organization-access_levels-access-level-names', args=[self.org.id])
        raw_result = self.client.post(
            url,
            data=json.dumps({"access_level_names": ["just one"]}),
            content_type='application/json',
        )
        assert raw_result.status_code == 400

        # adding multiple works
        url = reverse_lazy('api:v3:organization-access_levels-access-level-names', args=[self.org.id])
        raw_result = self.client.post(
            url,
            data=json.dumps({"access_level_names": ["one", "two"]}),
            content_type='application/json',
        )
        assert raw_result.status_code == 200
        assert Organization.objects.get(pk=self.org.id).access_level_names == ["one", "two"]

    def test_edit_access_level_names_duplicates(self):
        url = reverse_lazy('api:v3:organization-access_levels-access-level-names', args=[self.org.id])
        raw_result = self.client.post(
            url,
            data=json.dumps({"access_level_names": ["hip", "hip"]}),
            content_type='application/json',
        )
        assert raw_result.status_code == 400

    def test_edit_access_level_names_column_name_colision(self):
        url = reverse_lazy('api:v3:organization-access_levels-access-level-names', args=[self.org.id])
        raw_result = self.client.post(
            url,
            data=json.dumps({"access_level_names": ["Address Line 1"]}),
            content_type='application/json',
        )
        assert raw_result.status_code == 400

    def test_add_new_access_level_instance(self):
        self.org.access_level_names = ["1st gen", "2nd gen"]
        self.org.save()

        # get try to clear access_level_names
        url = reverse_lazy('api:v3:organization-access_levels-add-instance', args=[self.org.id])
        raw_result = self.client.post(
            url,
            data=json.dumps({"parent_id": self.org.root.pk, "name": "boo"}),
            content_type='application/json',
        )
        assert raw_result.status_code == 201

        # get new access_level_instance
        boo = AccessLevelInstance.objects.get(organization=self.org, name="boo")

        # check result
        result = json.loads(raw_result.content)
        assert result == {
            'access_level_names': ["1st gen", "2nd gen"],
            'access_level_tree': [{
                'id': self.org.root.pk,
                'data': {
                    'name': 'root',
                    'organization': self.org.id,
                    'path': {'1st gen': 'root'},
                },
                'children': [{
                    'id': boo.pk,
                    'data': {
                        'name': 'boo',
                        'organization': self.org.id,
                        'path': {'1st gen': 'root', '2nd gen': 'boo'},
                    }
                }]
            }],
        }

    def test_add_alis_from_file_bad1(self):
        """ This test makes sure that import files will fail when incorrect
        access level names (headers) are provided """
        self.org.access_level_names = ["top level", "Sector", "Sub Sector", "Partner"]
        self.org.save()

        filename = "access-levels-wrong1.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        uploaded_filepath = filepath
        url = reverse_lazy('api:v3:organization-access_levels-start-save-data', args=[self.org.id])
        raw_result = self.client.post(
            url,
            data=json.dumps({"filename": uploaded_filepath}),
            content_type='application/json'
        )
        # 200 - process ok
        assert raw_result.status_code == 200
        result = json.loads(raw_result.content)
        assert result['message'] == 'Invalid Column Name: "\'partner\'"'
        assert result['status'] == 'error'

    def test_add_alis_from_file_bad2(self):
        """ This test makes sure that import files will fail when additional
        access level columns that do not exist in the hierarchy are provided """
        self.org.access_level_names = ["top level", "Sector", "Sub Sector", "Partner"]
        self.org.save()

        filename = "access-levels-wrong2.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        uploaded_filepath = filepath
        url = reverse_lazy('api:v3:organization-access_levels-start-save-data', args=[self.org.id])
        raw_result = self.client.post(
            url,
            data=json.dumps({"filename": uploaded_filepath}),
            content_type='application/json'
        )
        # 200 - process finishes without crashing
        assert raw_result.status_code == 200
        result = json.loads(raw_result.content)
        assert result['message'] == {'Test Partner 1': {'message': "Error reading CSV data row: {'sector': 'Test', 'sub sector': 'Sub Test', 'partner': 'Test Partner 1', 'extra': 'wrong'}...no access level for column extra found"}}

    def test_add_alis_from_file_bad3(self):
        """ This test makes sure that import files will fail when the file
        is incorrectly filled out (no data in col 1 but data in col 2, etc.) """

        self.org.access_level_names = ["top level", "Sector", "Sub Sector", "Partner"]
        self.org.save()

        filename = "access-levels-wrong3.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        uploaded_filepath = filepath
        url = reverse_lazy('api:v3:organization-access_levels-start-save-data', args=[self.org.id])
        raw_result = self.client.post(
            url,
            data=json.dumps({"filename": uploaded_filepath}),
            content_type='application/json'
        )
        # 200 - process finishes without crashing
        assert raw_result.status_code == 200
        result = json.loads(raw_result.content)
        assert result['message'] == {'Test3 Partner2': {'message': "Blank value for column sector in CSV data row: {'sector': '', 'sub sector': 'Test3Sub2', 'partner': 'Test3 Partner2'}...skipping"}, 'Test3 Partner3': {'message': "Blank value for column sector in CSV data row: {'sector': '', 'sub sector': '', 'partner': 'Test3 Partner3'}...skipping"}}

    def test_add_access_level_instances_from_file(self):
        self.org.access_level_names = ["top level", "Sector", "Sub Sector", "Partner"]
        self.org.save()

        filename = "access-level-instances.xlsx"
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/data/" + filename

        uploaded_filepath = filepath
        url = reverse_lazy('api:v3:organization-access_levels-start-save-data', args=[self.org.id])
        raw_result = self.client.post(
            url,
            data=json.dumps({"filename": uploaded_filepath}),
            content_type='application/json'
        )

        assert raw_result.status_code == 200

        # todo: deal with the progress loop
        # instead of dealing with the progress loop, just wait a bit
        time.sleep(20)

        # spot check the tree now
        url = reverse_lazy('api:v3:organization-access_levels-tree', args=[self.org.id],)

        # get tree
        raw_result = self.client.get(url)
        result = json.loads(raw_result.content)
        assert result['access_level_tree'][0]['id'] == self.org.root.pk
        assert len(result['access_level_tree'][0]['children']) == 8
        assert len(result['access_level_tree'][0]['children'][0]['children'][0]['children']) == 8

        # retrieve the last access level instance
        _ = AccessLevelInstance.objects.get(organization=self.org, name="Company H")
