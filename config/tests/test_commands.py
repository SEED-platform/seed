"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import os
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import ROLE_OWNER, Organization, OrganizationUser


class ManagementTests(TestCase):
    """tests config django management commands"""

    @patch.dict(os.environ, {}, clear=True)
    def test_create_default_user(self):
        """tests the create_default_user management command"""
        # check default case
        call_command("create_default_user")
        self.assertTrue(User.objects.filter(username="demo@seed-platform.org").exists())
        self.assertTrue(Organization.objects.filter(name="demo").exists())
        self.assertTrue(OrganizationUser.objects.filter(user__username="demo@seed-platform.org", organization__name="demo").exists())

        u = User.objects.get(username="demo@seed-platform.org")
        self.assertTrue(u.check_password("demo"))

        output = StringIO()
        with patch.object(Organization, "add_member") as add_member:
            call_command("create_default_user", stdout=output)

        add_member.assert_not_called()
        self.assertIn("Org <demo> already exists; user is already an owner", output.getvalue())
        self.assertNotIn("adding user", output.getvalue())
        self.assertTrue(OrganizationUser.objects.filter(user=u, organization__name="demo", role_level=ROLE_OWNER).exists())

    @patch.dict(
        os.environ,
        {
            "SEED_ADMIN_USER": "environment@seed-platform.org",
            "SEED_ADMIN_PASSWORD": "environment-password",
            "SEED_ADMIN_ORG": "environment-org",
        },
        clear=True,
    )
    def test_create_default_user_from_environment(self):
        call_command("create_default_user")

        self.assertTrue(User.objects.filter(username="environment@seed-platform.org").exists())
        self.assertTrue(Organization.objects.filter(name="environment-org").exists())
        self.assertTrue(
            OrganizationUser.objects.filter(user__username="environment@seed-platform.org", organization__name="environment-org").exists()
        )
        user = User.objects.get(username="environment@seed-platform.org")
        self.assertTrue(user.check_password("environment-password"))

    @patch.dict(
        os.environ,
        {
            "SEED_ADMIN_USER": "environment@seed-platform.org",
            "SEED_ADMIN_PASSWORD": "environment-password",
            "SEED_ADMIN_ORG": "environment-org",
        },
        clear=True,
    )
    def test_create_default_user_arguments_override_environment(self):
        call_command(
            "create_default_user",
            username="argument@seed-platform.org",
            password="argument-password",
            organization="argument-org",
        )

        self.assertTrue(User.objects.filter(username="argument@seed-platform.org").exists())
        self.assertTrue(Organization.objects.filter(name="argument-org").exists())
        self.assertTrue(
            OrganizationUser.objects.filter(user__username="argument@seed-platform.org", organization__name="argument-org").exists()
        )
        user = User.objects.get(username="argument@seed-platform.org")
        self.assertTrue(user.check_password("argument-password"))
