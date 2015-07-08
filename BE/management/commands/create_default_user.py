# -*- coding: utf-8 -*-

# stdlib
from optparse import make_option

# Django
from django.core.management.base import BaseCommand

# app
from seed.landing.models import SEEDUser as User
from superperms.orgs.models import Organization, OrganizationUser


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--username',
                    default='demo@buildingenergy.com',
                    help='Sets the default username.',
                    action='store',
                    type='string',
                    dest='username'),
        make_option('--password',
                    default='demo',
                    help='Sets the default password',
                    action='store',
                    type='string',
                    dest='password'),
        make_option('--organization',
                    default='demo',
                    help='Sets the default organization',
                    action='store',
                    type='string',
                    dest='organization'),
    )
    # args = ''
    help = 'Creates a default super user for the system tied to an organization'

    def handle(self, *args, **options):
        if User.objects.filter(username=options['username']).exists():
            self.stdout.write(
                'User <%s> already exists' % options['username'],
                ending='\n'
            )
            u = User.objects.get(username=options['username'])
        else:
            self.stdout.write(
                'Creating user <%s>, password <%s> ...' % (
                    options['username'], options['password']
                ), ending=' '
            )
            u = User.objects.create_superuser(
                options['username'],
                options['username'],
                options['password']
            )
            self.stdout.write('Created!', ending='\n')

        org, created = Organization.objects.get_or_create(
            name=options['organization'])
        if created:
            self.stdout.write(
                'Creating org <%s> ... Created!' % options['organization'],
                ending='\n'
            )
        else:
            self.stdout.write(
                'Org <%s> aleady exists' % options['organization'], ending='\n'
            )

        self.stdout.write(
            'Creating org user ...', ending=' '
        )
        OrganizationUser.objects.create(user=u, organization=org)
        self.stdout.write('Created!', ending='\n')
