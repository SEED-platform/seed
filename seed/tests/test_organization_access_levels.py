# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json

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

    def test_edit_access_level_names_bad_names(self):
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

        # get try to add to few levels
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
