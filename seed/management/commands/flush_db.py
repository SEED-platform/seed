"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

This command is similar to `manage.py flush` except that it preserves the static EEEJ and Uniformat data
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Flush the database except for static tables"

    def handle(self, *args, **kwargs):
        tables_to_ignore = [
            "django_content_type",
            "django_migrations",
            "django_site",
            "seed_eeejcejst",
            "seed_eeejhud",
            "seed_uniformat",
        ]

        with connection.cursor() as cursor:
            all_tables = connection.introspection.table_names()
            for table in all_tables:
                if table not in tables_to_ignore:
                    cursor.execute(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE;')
                #     self.stdout.write(self.style.SUCCESS(f'Truncated table: {table}'))
                # else:
                #     self.stdout.write(self.style.WARNING(f'Skipped table: {table}'))
