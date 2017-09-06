# -*- coding: utf-8 -*-
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
# stdlib
from optparse import make_option

# Django
from django.core.management.base import BaseCommand

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization
# app
from seed.utils.organizations import create_organization


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--username',
                    default='demo@seed.lbl.gov',
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
                'Creating user <%s>, password <hidden> ...' % (options['username']), ending=' '
            )
            u = User.objects.create_superuser(
                options['username'],
                options['username'],
                options['password']
            )
            self.stdout.write('Creating API Key', ending='\n')
            u.generate_key()

            self.stdout.write('Created!', ending='\n')

        if Organization.objects.filter(name=options['organization']).exists():
            org = Organization.objects.get(name=options['organization'])
            self.stdout.write(
                'Org <%s> already exists' % options['organization'], ending='\n'
            )
        else:
            self.stdout.write(
                'Creating org <%s> ...' % options['organization'],
                ending=' '
            )
            org, _, user_added = create_organization(u, options['organization'])
            self.stdout.write('Created!', ending='\n')
