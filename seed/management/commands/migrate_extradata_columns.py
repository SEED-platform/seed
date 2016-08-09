from __future__ import unicode_literals

import itertools

from django.core.management.base import BaseCommand
from seed.lib.superperms.orgs.models import Organization
from _localtools import get_static_extradata_mapping_file

from _localtools import get_taxlot_columns
from _localtools import get_property_columns

from seed.models import BuildingSnapshot
import pdb

class Command(BaseCommand):
        def add_arguments(self, parser):
            parser.add_argument('--org', dest='organization', default=False)
            parser.add_argument('--stats', dest='stats', default=False, action="store_true")
            parser.add_argument('--create-columns', dest='create_columns', default=False, action="store_true")
            return

        def handle(self, *args, **options):
            # Process Arguments
            if options['organization']:
                organization_ids = map(int, options['organization'].split(","))
            else:
                organization_ids = get_core_organizations()

            for org_id in organization_ids:
                org = Organization.objects.get(pk=org_id)

                if options['stats']:
                    self.display_stats(org)

                if options['create_columns']:
                    self.copy_columns(org)
            return

        def display_stats(self, org):
            taxlot_columns = get_taxlot_columns(org)
            property_columns = get_property_columns(org)


            extra_data_columns = set(itertools.chain.from_iterable(map(lambda bs: bs.extra_data.keys(), BuildingSnapshot.objects.filter(super_organization=org, canonical_building__active=True).all())))
            mapped_columns = set(itertools.chain(taxlot_columns, property_columns))

            missing = [x for x in extra_data_columns if x not in mapped_columns and x.strip()]

            if len(missing):
                print "== org {}-{}: {} missing == ".format(org.pk, org.name, len(missing))
            for m in sorted(missing):
                print m

            return
