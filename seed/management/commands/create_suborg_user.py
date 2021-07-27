# -*- coding: utf-8 -*-
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.core.management.base import BaseCommand

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization
from seed.lib.superperms.orgs.models import ROLE_MEMBER, ROLE_OWNER, ROLE_VIEWER
from seed.utils.organizations import create_suborganization


class Command(BaseCommand):
    help = 'Creates a default super user for the system tied to an organization'

    def add_arguments(self, parser):
        parser.add_argument('--username',
                            default='demo@seed-platform.org',
                            help='Existing SEED User',
                            action='store',
                            dest='username')

        parser.add_argument('--parent_org',
                            default='demo',
                            help='Name of the parent organization',
                            action='store',
                            dest='parent_org')

        parser.add_argument('--suborg',
                            default='demo_sub',
                            help='Name of the sub-organization',
                            action='store',
                            dest='suborg')

        parser.add_argument('--suborg_role',
                            default='owner',
                            help='Role of suborg user',
                            action='store',
                            dest='suborg_role')

    def handle(self, *args, **options):
        if not User.objects.filter(username=options['username']).exists():
            self.stdout.write(
                'User \'%s\' does not exist, cannot create suborg' % options['username'],
                ending='\n'
            )
            exit(1)
        else:
            u = User.objects.get(username=options['username'])

        if not Organization.objects.filter(name=options['parent_org']).exists():
            self.stdout.write(
                'Parent organization \'%s\' does not exist, cannot create suborg' % options['parent_org'],
                ending='\n'
            )
            exit(1)
        else:
            org = Organization.objects.get(name=options['parent_org'])

        suborg_role = ROLE_OWNER
        if options['suborg_role'] == 'owner':
            suborg_role = ROLE_OWNER
        elif options['suborg_role'] == 'member':
            suborg_role = ROLE_MEMBER
        elif options['suborg_role'] == 'viewer':
            suborg_role = ROLE_VIEWER
        else:
            raise Exception("Invalid role for suborg user. Expecting owner, member, or viewer.")

        create_suborganization(u, org, options['suborg'], suborg_role)
        self.stdout.write('Sub-organization created!', ending='\n')
