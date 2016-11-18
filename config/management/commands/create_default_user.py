# -*- coding: utf-8 -*-
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
# stdlib
from datetime import date, datetime, timedelta
from optparse import make_option

# Django
from django.core.management.base import BaseCommand

# app
from seed.utils.organizations import create_organization
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization
from seed.models import Cycle


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

        year = date.today().year - 1
        cycle_name = str(year) + ' Calendar Year'
        if Cycle.objects.filter(name=cycle_name, organization=org).exists():
            self.stdout.write(
                'Cycle <%s> already exists' % cycle_name,
                ending='\n'
            )
            c = Cycle.objects.get(name=cycle_name, organization=org)
        else:
            self.stdout.write(
                'Creating cycle <%s> ...' % cycle_name,
                ending=' '
            )
            c = Cycle.objects.create(name=cycle_name,
                                     organization=org,
                                     start=datetime(year, 1, 1),
                                     end=datetime(year + 1, 1, 1) - timedelta(seconds=1)
                                     )
            self.stdout.write('Created!', ending='\n')
