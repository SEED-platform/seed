# -*- coding: utf-8 -*-
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.core.management.base import BaseCommand

from seed.lib.superperms.orgs.models import Organization
from seed.models import Column
from seed.utils.organizations import _create_default_columns


class Command(BaseCommand):
    help = 'Creates the default columns of an organization if there are none'

    def add_arguments(self, parser):
        parser.add_argument('--org_id',
                            default=None,
                            help='Organization to add default columns',
                            action='store')

    def handle(self, *args, **options):
        if options['org_id']:
            orgs = Organization.objects.filter(pk=options['org_id'])
        else:
            orgs = Organization.objects.all().order_by('id')

        for org in orgs:
            self.stdout.write("Checking if organization %s has any columns" % org.id)
            if Column.objects.filter(organization=org).count() == 0:
                self.stdout.write("  Organization has no columns, adding")
                _create_default_columns(org.id)
            else:
                self.stdout.write("  Organization already has columns, skipping")
