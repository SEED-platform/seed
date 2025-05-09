"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core.management.base import BaseCommand

from seed.lib.superperms.orgs.models import Organization
from seed.models import User


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--user", dest="user", default=False)
        parser.add_argument("--user-id", dest="user_id", default=False, type=int)
        parser.add_argument("--stats", dest="stats_only", default=False, action="store_true")
        parser.add_argument("--force", dest="force", default=False, action="store_true")

    def display_stats(self):
        print("Showing users:")
        for ndx, user in enumerate(User.objects.order_by("id").all()):
            print(f"   id={user.pk}, username={user.username}")

    def handle(self, *args, **options):
        if options["stats_only"]:
            self.display_stats()
            return

        if options["user"] and options["user_id"]:
            print("Both --user and --user-id is set, using --user_id and ignoring --user.")
            options["user"] = False

        if not options["user"] and not options["user_id"]:
            print("Must set either --user and --user-id to add user, or run with --stats to display the users.  Nothing for me to do here.")
            return

        if options["user"]:
            query = User.objects.filter(username=options["user"])
            if not query.count():
                print("No user by the name '{}' was found.  Run with --stats to display all users.")
                return
            user = query.first()

        if options["user_id"]:
            try:
                user = User.objects.get(pk=options["user_id"])
            except AttributeError:
                print(f"No user with id={options['user_id']} was found.  Run with --stats to display all the users.")
                return

        organizations = list(Organization.objects.all())

        if not options["force"]:
            print(f"Add user {user} to organizations?")
            for ndx, org in enumerate(organizations):
                print(f"   {ndx}: {org}")
            if not input("Continue? [y/N]").lower().startswith("y"):
                print("Quitting.")
                return

        for org in organizations:
            print(f"Adding user to {org}.")
            org.add_member(user, access_level_instance_id=org.root.id)
        # NL added this but is not going to make it the default because it may cause
        # security issues for others. Not sure yet. Comment here if you think we should
        # by default make the user a superuser in this script:
        #
        # user.is_superuser = True
        user.save()  # One for good measure

        print("Done!")

        return
