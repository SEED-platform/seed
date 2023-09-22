"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.core.management.base import BaseCommand

from seed.lib.geospatial.eeej import add_eeej_data


class Command(BaseCommand):
    help = 'Add EEEJ Data: HUD and CEJST'

    def handle(self, *args, **options):

        add_eeej_data()
        print("done!")
