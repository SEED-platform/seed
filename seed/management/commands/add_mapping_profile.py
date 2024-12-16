"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import csv
import locale
import os
import sys

from django.core.management.base import BaseCommand

from seed.lib.superperms.orgs.models import Organization


class Command(BaseCommand):
    help = "Add a mapping profile to an organization from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument("--organization_name", help="Organization name", action="store")

        parser.add_argument(
            "--csv_file",
            help="Mapping profile CSV file, must follow specific format. Relative to location " "of manage.py call.",
            action="store",
            required=True,
        )

        parser.add_argument("--name", help="Name of the mapping profile", action="store")

        parser.add_argument("--overwrite", help="Overwrite if column mapping profile name exists", action="store_true")

    def handle(self, *args, **options):
        # verify that the user exists
        org = Organization.objects.filter(name=options["organization_name"]).first()
        if not org:
            self.stdout.write(f"No organization found for {options['organization_name']}")
            sys.exit(1)

        if not os.path.exists(options["csv_file"]):
            self.stdout.write(f"Mapping CSV file does not exist: {options['csv_file']}")
            sys.exit(1)

        mappings = []
        with open(options["csv_file"], encoding=locale.getpreferredencoding(False)) as f:
            data = csv.reader(f, delimiter=",", quotechar='"')
            next(data)  # skip the header row
            for row in data:
                units = row[1]
                if units == "":
                    units = None
                mappings.append(
                    {
                        "from_field": row[0],
                        "from_units": units,
                        "to_table_name": row[2],
                        "to_field": row[3],
                    }
                )

        # create the mapping profile
        cmp, created = org.columnmappingprofile_set.get_or_create(name=options["name"])
        if not created and not options["overwrite"]:
            self.stdout.write(f"Column mapping profile already exists: {options['name']}")
            self.stdout.write("Pass --overwrite to overwrite existing mappings in profile if desired")
            sys.exit(0)

        cmp.mappings = mappings
        cmp.save()

        self.stdout.write(f"Finished adding column mapping profile for {options['name']}")
