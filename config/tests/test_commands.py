"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.core.management import call_command
from django.test import TestCase

from seed.lib.superperms.orgs.models import Organization, OrganizationUser

from seed.landing.models import SEEDUser as User


class ManagementTests(TestCase):
    "tests config django management commands"

    def test_create_default_user(self):
        """tests the create_default_user management command"""
        # check default case
        call_command('create_default_user')
        self.assertTrue(User.objects.filter(
            username='demo@seed-platform.org').exists())
        self.assertTrue(Organization.objects.filter(name='demo').exists())
        self.assertTrue(OrganizationUser.objects.filter(
            user__username='demo@seed-platform.org',
            organization__name='demo'
        ).exists())

        u = User.objects.get(username='demo@seed-platform.org')
        u.check_password('demo')

        # check custom user case
        call_command(
            'create_default_user',
            username='demo_user_2@seed-platform.org',
            password='demo123',
            organization='demo_org_2'
        )
        self.assertTrue(User.objects.filter(
            username='demo_user_2@seed-platform.org').exists())
        self.assertTrue(Organization.objects.filter(name='demo_org_2').exists())
        self.assertTrue(OrganizationUser.objects.filter(
            user__username='demo_user_2@seed-platform.org',
            organization__name='demo_org_2'
        ).exists())
        u = User.objects.get(username='demo_user_2@seed-platform.org')
        u.check_password('demo123')
