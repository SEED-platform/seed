from __future__ import unicode_literals

from django.core.management.base import BaseCommand
from _localtools import get_static_extradata_mapping_file

class Command(BaseCommand):
        def add_arguments(self, parser):
            return

        def handle(self, *args, **options):
            # if options['warn': pass

            print get_static_extradata_mapping_file()

            _load_raw_mapping_data()
            return
