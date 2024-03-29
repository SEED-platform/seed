# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import pytest
from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.utils.organizations import create_organization


class TestOrganizationAccessLevels(TestCase):
    def setUp(self):
        user_details = {'username': 'test_user@demo.com', 'password': 'test_pass', 'email': 'test_user@demo.com'}
        self.fake_user = User.objects.create_user(**user_details)

    def test_tree_on_create(self):
        fake_org, _, _ = create_organization(self.fake_user, 'Organization A')

        # has right access_level_names
        assert fake_org.access_level_names == ['Organization A']

        # has right AccessLevelInstances
        assert AccessLevelInstance.objects.filter(organization=fake_org).count() == 1
        root = fake_org.root
        assert root.name == 'root'

        # get right access_tree
        assert fake_org.get_access_tree() == [
            {
                'id': root.pk,
                'data': {
                    'name': 'root',
                    'organization': fake_org.id,
                    'path': {'Organization A': 'root'},
                },
            }
        ]

    def test_create_level_instance_without_name(self):
        fake_org, _, _ = create_organization(self.fake_user, 'Organization A')

        # create access level instance on an unnamed Instance
        with pytest.raises(Exception):  # noqa: PT011
            fake_org.add_new_access_level_instance(fake_org.root.id, 'mom')

    def test_build_out_tree(self):
        fake_org, _, _ = create_organization(self.fake_user, 'Organization A')

        # populate tree
        fake_org.access_level_names += ['2nd gen', '3rd gen']
        fake_org.save()
        aunt = fake_org.add_new_access_level_instance(fake_org.root.id, 'aunt')
        mom = fake_org.add_new_access_level_instance(fake_org.root.id, 'mom')
        me = fake_org.add_new_access_level_instance(mom.id, 'me')

        # get tree
        assert fake_org.get_access_tree() == [
            {
                'id': fake_org.root.pk,
                'data': {
                    'name': 'root',
                    'organization': fake_org.id,
                    'path': {'Organization A': 'root'},
                },
                'children': [
                    {
                        'id': aunt.pk,
                        'data': {
                            'name': 'aunt',
                            'organization': fake_org.id,
                            'path': {'Organization A': 'root', '2nd gen': 'aunt'},
                        },
                    },
                    {
                        'id': mom.pk,
                        'data': {
                            'name': 'mom',
                            'organization': fake_org.id,
                            'path': {'Organization A': 'root', '2nd gen': 'mom'},
                        },
                        'children': [
                            {
                                'id': me.pk,
                                'data': {
                                    'name': 'me',
                                    'organization': fake_org.id,
                                    'path': {'Organization A': 'root', '2nd gen': 'mom', '3rd gen': 'me'},
                                },
                            }
                        ],
                    },
                ],
            }
        ]

    def test_get_path(self):
        fake_org, _, _ = create_organization(self.fake_user, 'Organization A')

        # populate tree
        fake_org.access_level_names += ['2nd gen', '3rd gen']
        fake_org.save()
        fake_org.add_new_access_level_instance(fake_org.root.id, 'aunt')
        mom = fake_org.add_new_access_level_instance(fake_org.root.id, 'mom')
        me = fake_org.add_new_access_level_instance(mom.id, 'me')

        assert me.get_path() == {
            'Organization A': 'root',
            '2nd gen': 'mom',
            '3rd gen': 'me',
        }
