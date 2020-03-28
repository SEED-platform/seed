# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
Tests related to sharing of data between users, orgs, suborgs, etc.
"""

from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import (
    Organization,
    ROLE_OWNER,
    ROLE_MEMBER
)


class SharingViewTests(TestCase):
    """
    Tests of the SEED search_buildings
    """

    def setUp(self):
        self.admin_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'show_shared_buildings': True
        }
        self.admin_user = User.objects.create_superuser(**self.admin_details)
        self.parent_org = Organization.objects.create(name='Parent')
        self.parent_org.add_member(self.admin_user, ROLE_OWNER)

        self.eng_user_details = {
            'username': 'eng_owner@demo.com',
            'password': 'eng_pass',
            'email': 'eng_owner@demo.com'
        }
        self.eng_user = User.objects.create_user(**self.eng_user_details)
        self.eng_org = Organization.objects.create(parent_org=self.parent_org,
                                                   name='Engineers')
        self.eng_org.add_member(self.eng_user, ROLE_OWNER)

        self.des_user_details = {
            'username': 'des_owner@demo.com',
            'password': 'des_pass',
            'email': 'des_owner@demo.com'
        }
        self.des_user = User.objects.create_user(**self.des_user_details)
        self.des_org = Organization.objects.create(parent_org=self.parent_org,
                                                   name='Designers')
        self.des_org.add_member(self.des_user, ROLE_MEMBER)

    def test_scenario(self):
        """
        Make sure setUp works.
        """
        self.assertTrue(self.des_org in self.parent_org.child_orgs.all())
        self.assertTrue(self.eng_org in self.parent_org.child_orgs.all())
        self.assertTrue(self.parent_org.is_owner(self.admin_user))
        self.assertFalse(self.parent_org.is_owner(self.eng_user))
        self.assertFalse(self.parent_org.is_owner(self.des_user))
        self.assertFalse(self.des_org.is_owner(self.des_user))
        self.assertTrue(self.des_org.is_member(self.des_user))
        self.assertTrue(self.eng_org.is_owner(self.eng_user))
