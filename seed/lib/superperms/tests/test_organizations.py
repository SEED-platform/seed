# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import ROLE_VIEWER
from seed.utils.organizations import create_organization, create_suborganization


class TestOrganizations(TestCase):
    """Test the clean methods on the organization."""

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.fake_user = User.objects.create_user(**user_details)
        self.fake_org, _, _ = create_organization(self.fake_user, 'Organization A')

    def test_parent_org(self):
        self.assertEqual(self.fake_org.is_parent, True)

    def test_suborgs_parent(self):
        user_details_2 = {
            'username': 'test_user_2@demo.com',
            'password': 'test_pass',
            'email': 'test_user_2@demo.com'
        }
        user2 = User.objects.create(**user_details_2)

        created, suborg, org_user = create_suborganization(
            user2, self.fake_org, 'sub org name', ROLE_VIEWER
        )
        self.assertTrue(created)
        self.assertEqual(suborg.name, 'sub org name')
        self.assertFalse(suborg.is_parent)
        self.assertTrue(suborg.is_member(user2))
        self.assertFalse(suborg.is_member(self.fake_user))

        self.assertEqual(org_user.role_level, ROLE_VIEWER)

    def test_too_many_nested(self):
        user_details_2 = {
            'username': 'test_user_2@demo.com',
            'password': 'test_pass',
            'email': 'test_user_2@demo.com'
        }
        user2 = User.objects.create(**user_details_2)

        user_details_3 = {
            'username': 'test_user_3@demo.com',
            'password': 'test_pass',
            'email': 'test_user_3@demo.com'
        }
        user3 = User.objects.create(**user_details_3)
        created, suborg, org_user = create_suborganization(user2, self.fake_org, 'sub org name')
        self.assertTrue(created)

        created, message, org_user = create_suborganization(user3, suborg, 'sub org of sub org')
        self.assertFalse(created)
        self.assertEqual(message, 'Tried to create child of a child organization.')
