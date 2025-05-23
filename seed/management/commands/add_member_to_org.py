"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import sys

from django.core.management.base import BaseCommand

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import ROLE_MEMBER, ROLE_OWNER, ROLE_VIEWER, Organization, OrganizationUser


class Command(BaseCommand):
    help = "Add an existing member to an existing organization"

    def add_arguments(self, parser):
        parser.add_argument("--username", help="Name of the existing user (email address)", action="store")

        parser.add_argument("--organization_name", help="Organization name", action="store")

        # type of member
        parser.add_argument("--member_type", default="member", help="Type of member: owner, member, viewer", action="store")

    def handle(self, *args, **options):
        # verify that the user exists
        org = Organization.objects.filter(name=options["organization_name"]).first()
        if not org:
            self.stdout.write(f"No organization found for {options['organization_name']}")
            sys.exit(1)

        u = User.objects.filter(username=options["username"]).first()
        if not u:
            self.stdout.write(f"No user found for {options['username']}")
            sys.exit(1)

        ou, _ = OrganizationUser.objects.get_or_create(user=u, organization=org)
        if options["member_type"] == "viewer":
            ou.role_level = ROLE_VIEWER
        elif options["member_type"] == "owner":
            ou.role_level = ROLE_OWNER
        else:
            ou.role_level = ROLE_MEMBER
        ou.save()

        self.stdout.write(f"Added user {u.username} to org {org.name} with permissions as {options['member_type']}")
