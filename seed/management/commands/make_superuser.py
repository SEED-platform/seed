# -*- coding: utf-8 -*-
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from __future__ import unicode_literals

from django.core.management.base import BaseCommand

from seed.lib.superperms.orgs.models import Organization
from seed.models import User


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--user', dest='user', default=False)
        parser.add_argument('--user-id', dest='user_id', default=False, type=int)
        parser.add_argument('--stats', dest='stats_only', default=False, action='store_true')
        parser.add_argument('--force', dest='force', default=False, action='store_true')

    def display_stats(self):
        print("Showing users:")
        for (ndx, user) in enumerate(User.objects.order_by('id').all()):
            print("   id={}, username={}".format(user.pk, user.username))

    def handle(self, *args, **options):
        if options['stats_only']:
            self.display_stats()
            return

        if options['user'] and options['user_id']:
            print("Both --user and --user-id is set, using --user_id and ignoring --user.")
            options['user'] = False

        if not options['user'] and not options['user_id']:
            print("Must set either --user and --user-id to add user, or run with --stats to display the users.  Nothing for me to do here.")
            return

        if options['user']:
            query = User.objects.filter(username=options['user'])
            if not query.count():
                print("No user by the name '{}' was found.  Run with --stats to display all users.")
                return
            user = query.first()

        if options['user_id']:
            try:
                user = User.objects.get(pk=options['user_id'])
            except AttributeError:
                print("No user with id={} was found.  Run with --stats to display all the users.".format(options['user_id']))
                return

        organizations = list(Organization.objects.all())

        if not options['force']:
            print("Add user {} to organizations?".format(user))
            for (ndx, org) in enumerate(organizations):
                print("   {}: {}".format(ndx, org))
            if not input("Continue? [y/N]").lower().startswith("y"):
                print("Quitting.")
                return

        for org in organizations:
            print("Adding user to {}.".format(org))
            org.add_member(user)
        else:
            # NL added this but is not going to make it the default because it may cause
            # security issues for others. Not sure yet. Comment here if you think we should
            # by default make the user a superuser in this script:
            #
            # user.is_superuser = True
            user.save()  # One for good measure

        print("Done!")

        return
