# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.utils.organizations import create_organization


class TestOrganizationAccessLevels(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.fake_user = User.objects.create_user(**user_details)

    def test_tree_on_create(self):
        fake_org, _, _ = create_organization(self.fake_user, 'Organization A')

        # has right access_level_names
        assert fake_org.access_level_names == ["Organization A"]

        # has right AccessLevelInstances
        assert AccessLevelInstance.objects.filter(organization=fake_org).count() == 1
        root = AccessLevelInstance.objects.get(organization=fake_org)
        assert root.name == "root"

        # get right access_tree
        assert fake_org.get_access_tree() == [
            {
                'id': root.pk,
                'data': {'name': 'root', 'organization': fake_org.id},
            }
        ]

    def test_create_level_instance_without_name(self):
        fake_org, _, _ = create_organization(self.fake_user, 'Organization A')
        root = AccessLevelInstance.objects.get(organization=fake_org)

        # create access level instance on an unnamed Instance
        with self.assertRaises(Exception):
            fake_org.add_new_access_level_instance(root.id, "mom")

    def test_build_out_tree(self):
        fake_org, _, _ = create_organization(self.fake_user, 'Organization A')

        # populate tree
        fake_org.access_level_names += ["2nd gen", "3rd gen"]
        fake_org.save()
        root = AccessLevelInstance.objects.get(organization=fake_org)
        aunt = fake_org.add_new_access_level_instance(root.id, "aunt")
        mom = fake_org.add_new_access_level_instance(root.id, "mom")
        me = fake_org.add_new_access_level_instance(mom.id, "me")

        # get tree
        assert fake_org.get_access_tree() == [
            {
                'id': root.pk,
                'data': {'name': 'root', 'organization': fake_org.id},
                'children': [
                    {'id': aunt.pk, 'data': {'name': 'aunt', 'organization': fake_org.id}},
                    {
                        'id': mom.pk,
                        'data': {'name': 'mom', 'organization': fake_org.id},
                        'children': [
                            {'id': me.pk, 'data': {'name': 'me', 'organization': fake_org.id}}
                        ]
                    }
                ]
            }
        ]
