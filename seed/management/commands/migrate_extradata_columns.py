from __future__ import unicode_literals

import itertools

from django.core.management.base import BaseCommand
from seed.lib.superperms.orgs.models import Organization
from _localtools import get_static_extradata_mapping_file

from _localtools import get_taxlot_columns
from _localtools import get_property_columns

from IPython import embed
from seed.models import BuildingSnapshot
from seed.models import Column
from seed.models import ColumnMapping
from seed.models import PropertyView
from seed.models import PropertyState
from seed.models import TaxLotView
from seed.models import TaxLotState
import pdb

class Command(BaseCommand):
        def add_arguments(self, parser):
            parser.add_argument('--org', dest='organization', default=False)
            parser.add_argument('--stats', dest='stats', default=False, action="store_true")

            parser.add_argument('--no-update-columns', dest='update_columns', default=True, action="store_false")
            parser.add_argument('--update-columns', dest='update_columns', default=True, action="store_true")

            parser.add_argument('--no-add-unmapped-columns', dest='add_unmapped_columns', default=False, action="store_false")
            parser.add_argument('--add-unmapped-columns', dest='add_unmapped_columns', default=False, action="store_true")

            parser.add_argument('--no-create-missing-columns', dest='create_missing_columns', default=False, action="store_true")
            parser.add_argument('--create-missing-columns', dest='create_missing_columns', default=False, action="store_true")
            return

        def handle(self, *args, **options):
            # Process Arguments
            if options['organization']:
                organization_ids = map(int, options['organization'].split(","))
            else:
                organization_ids = get_core_organizations()

            display_stats = options['stats']

            update_columns = options['update_columns']
            add_unmapped_columns = options['add_unmapped_columns']
            create_missing_columns = options['create_missing_columns']

            if display_stats:
                update_columns, add_unmapped_columns, search_missing_columns = False * 3

            for org_id in organization_ids:
                org = Organization.objects.get(pk=org_id)

                self.update_columns(org, update_columns, add_unmapped_columns)
                self.find_missing_columns(org, create=create_missing_columns)

            return

        def find_missing_columns(self, org, create):
            print "Creating missing columns for {}".format(org)

            property_views = PropertyView.objects.filter(property__organization=org).select_related('state').all()
            taxlot_views = TaxLotView.objects.filter(taxlot__organization=org).select_related('state').all()

            property_keys = set(itertools.chain.from_iterable(map(lambda v: v.state.extra_data.keys(), property_views)))
            taxlot_keys = set(itertools.chain.from_iterable(map(lambda v: v.state.extra_data.keys(), taxlot_views)))

            for pk in property_keys:
                qry = Column.objects.filter(organization=org,column_name=pk)
                cnt = qry.count()

                if not cnt:
                    if create:
                        print "Creating missing column {}".format(pk)
                        col = Column(organization = org, column_name = pk, is_extra_data=True, extra_data_source=Column.SOURCE_PROPERTY)
                        col.save()
                    else:
                        print "Missing column {}".format(pk)

            for tlk in taxlot_keys:
                qry = Column.objects.filter(organization=org,column_name=tlk)
                cnt = qry.count()

                if not cnt:
                    if create:
                        print "Creating missing column {}".format(tlk)
                        col = Column(organization = org, column_name = tlk, is_extra_data=True, extra_data_source=Column.SOURCE_PROPERTY)
                        col.save()
                    else:
                        print "Missing column {}".format(tlk)

            return

        def update_columns(self, org, update_columnms = True, create_missing = False):
            print "Updating  columns for org {}".format(org)
            taxlot_columns = get_taxlot_columns(org)
            property_columns = get_property_columns(org)
            columns = Column.objects.filter(organization = org).all()

            found = 0
            notfound = 0

            for tl_col in taxlot_columns:
                qry = Column.objects.filter(organization=org,column_name=tl_col)
                cnt = qry.count()
                if cnt:
                    # Update the column
                    col = qry.first()
                    col.extra_data_source = Column.SOURCE_TAXLOT
                    print "Setting Column {} to SOURCE_TAXLOT".format(col)
                    col.save()
                elif create_missing:
                    # Create the missing column
                    col = Column(organization = org, column_name = tl_col, is_extra_data=True, extra_data_source=Column.SOURCE_TAXLOT)
                    print "CREATING COLUMN {}".format(col)
                    col.save()

            for prop_col in property_columns:
                qry = Column.objects.filter(organization=org,column_name=prop_col)
                cnt = qry.count()
                if cnt:
                    # Update the column
                    col = qry.first()
                    print "Setting Column {} to SOURCE_TAXLOT".format(col)
                    col.extra_data_source = Column.SOURCE_PROPERTY
                    col.save()
                elif create_missing:
                    # Create the missing column
                    col = Column(organization = org, column_name = prop_col, is_extra_data=True, extra_data_source=Column.SOURCE_PROPERTY)
                    print "CREATING COLUMN {}".format(col)
                    col.save()
            return

        # def display_stats(self, org):
        #     taxlot_columns = get_taxlot_columns(org)
        #     property_columns = get_property_columns(org)


        #     extra_data_columns = set(itertools.chain.from_iterable(map(lambda bs: bs.extra_data.keys(), BuildingSnapshot.objects.filter(super_organization=org, canonical_building__active=True).all())))
        #     mapped_columns = set(itertools.chain(taxlot_columns, property_columns))

        #     missing = [x for x in extra_data_columns if x not in mapped_columns and x.strip()]

        #     if len(missing):
        #         print "== org {}-{}: {} missing == ".format(org.pk, org.name, len(missing))
        #     for m in sorted(missing):
        #         print m

        #     return
