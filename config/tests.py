"""
:copyright (c) 2014 - 2015, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.core.management import call_command
from django.test import TestCase

from seed.lib.superperms.orgs.models import Organization, OrganizationUser

from seed.landing.models import SEEDUser as User


class ManagementTests(TestCase):
    "tests config django management commands"

    def test_create_default_user(self):
        """tests the creat_default_user mgmt command"""
        # check default case
        call_command('create_default_user')
        self.assertTrue(User.objects.filter(
            username='demo@seed.lbl.gov').exists())
        self.assertTrue(Organization.objects.filter(name='demo').exists())
        self.assertTrue(OrganizationUser.objects.filter(
            user__username='demo@seed.lbl.gov',
            organization__name='demo'
        ).exists())
        u = User.objects.get(username='demo@seed.lbl.gov')
        u.check_password('demo')

        # check custom user case
        call_command(
            'create_default_user',
            username='bd@seed.lbl.gov',
            password='demo123',
            organization='bd'
        )
        self.assertTrue(User.objects.filter(
            username='bd@seed.lbl.gov').exists())
        self.assertTrue(Organization.objects.filter(name='bd').exists())
        self.assertTrue(OrganizationUser.objects.filter(
            user__username='bd@seed.lbl.gov',
            organization__name='bd'
        ).exists())
        u = User.objects.get(username='bd@seed.lbl.gov')
        u.check_password('demo123')
