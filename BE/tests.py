from django.core.management import call_command
from django.test import TestCase

from superperms.orgs.models import Organization, OrganizationUser

from landing.models import SEEDUser as User


class ManagementTests(TestCase):
    "tests BE django management commands"

    def test_create_default_user(self):
        """tests the creat_default_user mgmt command"""
        # check default case
        call_command('create_default_user')
        self.assertTrue(User.objects.filter(
            username='demo@buildingenergy.com').exists())
        self.assertTrue(Organization.objects.filter(name='demo').exists())
        self.assertTrue(OrganizationUser.objects.filter(
            user__username='demo@buildingenergy.com',
            organization__name='demo'
        ).exists())
        u = User.objects.get(username='demo@buildingenergy.com')
        u.check_password('demo')

        # check custom user case
        call_command(
            'create_default_user',
            username='bd@be.com',
            password='demo123',
            organization='bd'
        )
        self.assertTrue(User.objects.filter(
            username='bd@be.com').exists())
        self.assertTrue(Organization.objects.filter(name='bd').exists())
        self.assertTrue(OrganizationUser.objects.filter(
            user__username='bd@be.com',
            organization__name='bd'
        ).exists())
        u = User.objects.get(username='bd@be.com')
        u.check_password('demo123')
