# -*- coding: utf-8 -*-
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import csv
import os

from django.core.management.base import BaseCommand

from seed.lib.superperms.orgs.models import (
    Organization,
)


class Command(BaseCommand):
    help = 'Add a mapping profile to an organization from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('--organization_name',
                            help='Organization name',
                            action='store')

        parser.add_argument('--csv_file',
                            help='Mapping profile CSV file, must follow specific format. Relative to location '
                                 'of manage.py call.',
                            action='store',
                            required=True)

        parser.add_argument('--name',
                            help='Name of the mapping profile',
                            action='store')

        parser.add_argument('--overwrite',
                            help='Overwrite if column mapping profile name exists',
                            action='store_true')

    def handle(self, *args, **options):
        # verify that the user exists
        org = Organization.objects.filter(name=options['organization_name']).first()
        if not org:
            self.stdout.write("No organization found for %s" % options['organization_name'])
            exit(1)

        if not os.path.exists(options['csv_file']):
            self.stdout.write(f"Mapping CSV file does not exist: {options['csv_file']}")
            exit(1)

        mappings = []
        with open(options['csv_file'], 'r') as f:
            data = csv.reader(f, delimiter=',', quotechar="\"")
            data.__next__()  # skip the header row
            for row in data:
                units = row[1]
                if units == '':
                    units = None
                mappings.append(
                    {
                        'from_field': row[0],
                        'from_units': units,
                        'to_table_name': row[2],
                        'to_field': row[3],
                    }
                )

        # create the mapping profile
        cmp, created = org.columnmappingprofile_set.get_or_create(name=options['name'])
        if not created and not options['overwrite']:
            self.stdout.write(f"Column mapping profile already exists: {options['name']}")
            self.stdout.write("Pass --overwrite to overwrite existing mappings in profile if desired")
            exit(0)

        cmp.mappings = mappings
        cmp.save()

        self.stdout.write(f"Finished adding column mapping profile for {options['name']}")
