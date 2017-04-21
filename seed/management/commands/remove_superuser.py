from __future__ import unicode_literals

from django.core.management.base import BaseCommand

from seed.lib.superperms.orgs.models import Organization
from seed.models import User


# from seed.landing.models import DoesNotExist


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--user', dest='user', default=False)
        parser.add_argument('--user-id', dest='user_id', default=False, type=int)
        parser.add_argument('--remove', dest='force', default=False)
        return

    def handle(self, *args, **options):
        if options['user'] and options['user_id']:
            print "Both --user and --user-id is set, using --user_id and ignoring --user."
            options['user'] = False

        if not options['user'] and not options['user_id']:
            print "Must set either --user and --user-id to add user, or run with --stats to display the users.  Nothing for me to do here."
            return

        if options['user']:
            query = User.objects.filter(username=options['user'])
            if not query.count():
                print "No user by the name '{}' was found.  Run with --stats to display all users."
                return
            user = query.first()

        if options['user_id']:
            try:
                user = User.objects.get(pk=options['user_id'])
            except AttributeError, xcpt:
                print "No user with id={} was found.  Run with --stats to display all the users.".format(
                    options['user_id'])
                return

        user.is_superuser = False
        user.save()  # One for good measure

        print "Done!"

        return
