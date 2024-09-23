"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core.management.base import BaseCommand

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import ROLE_OWNER, Organization
from seed.utils.organizations import create_organization


class Command(BaseCommand):
    help = "Creates a default super user for the system tied to an organization"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username", default="demo@seed-platform.org", help="Sets the default username.", action="store", dest="username"
        )

        parser.add_argument("--password", default="demo", help="Sets the default password", action="store", dest="password")

        parser.add_argument("--organization", default="demo", help="Sets the default organization", action="store", dest="organization")

        parser.add_argument(
            "--type", default="superuser", help="Type of user to create, defaults to superuser", action="store", dest="usertype"
        )

    def handle(self, *args, **options):
        if User.objects.filter(username=options["username"]).exists():
            self.stdout.write(f"User <{options['username']}> already exists", ending="\n")
            u = User.objects.get(username=options["username"])
        else:
            self.stdout.write(f"Creating user <{options['username']}>, password <hidden> ...", ending=" ")

            if options["usertype"] == "superuser":
                u = User.objects.create_superuser(options["username"].lower(), options["username"], options["password"])
            else:
                u = User.objects.create_user(options["username"].lower(), options["username"], options["password"])

            self.stdout.write("Creating API Key", ending="\n")
            u.generate_key()

            self.stdout.write("Created!", ending="\n")

        if Organization.objects.filter(name=options["organization"]).exists():
            org = Organization.objects.get(name=options["organization"])
            self.stdout.write(f"Org <{options['organization']}> already exists, adding user", ending="\n")
            org.add_member(u, org.root.id, ROLE_OWNER)
        else:
            self.stdout.write(f"Creating org <{options['organization']}> ...", ending=" ")
            org, _, _user_added = create_organization(u, options["organization"])
            self.stdout.write("Created!", ending="\n")
