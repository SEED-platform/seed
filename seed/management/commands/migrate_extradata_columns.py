"""Make sure the columns are updated """

from __future__ import unicode_literals

import itertools

from django.core.management.base import BaseCommand
from seed.lib.superperms.orgs.models import Organization
from _localtools import get_static_extradata_mapping_file

from _localtools import get_taxlot_columns
from _localtools import get_property_columns
from _localtools import get_core_organizations
from _localtools import logging_info
from _localtools import logging_debug

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

        parser.add_argument('--no-update-columns', dest='update_columns', default=True, action="store_false")
        parser.add_argument('--update-columns',    dest='update_columns', default=True, action="store_true")

        parser.add_argument('--no-add-unmapped-columns', dest='add_unmapped_columns', default=True, action="store_false")
        parser.add_argument('--add-unmapped-columns',    dest='add_unmapped_columns', default=True, action="store_true")

        parser.add_argument('--no-create-missing-columns', dest='create_missing_columns', default=True, action="store_false")
        parser.add_argument('--create-missing-columns',    dest='create_missing_columns', default=True, action="store_true")
        return

    def handle(self, *args, **options):
        logging_info(
            "RUN migrate_extradata_columns with args={},kwds={}".format(args, options))

        if options['organization']:
            organization_ids = map(int, options['organization'].split(","))
        else:
            organization_ids = get_core_organizations()

        update_columns = options['update_columns']
        add_unmapped_columns = options['add_unmapped_columns']
        create_missing_columns = options['create_missing_columns']

        for org_id in organization_ids:
            org = Organization.objects.get(pk=org_id)

            # Update
            if update_columns:
                self.update_columns_based_on_mappings_file(org)

            if create_missing_columns:
                self.find_missing_columns_based_on_extra_data(org)

        logging_info("END migrate_extradata_columns")
        return

    def find_missing_columns_based_on_extra_data(self, org):
        """Look through all the extra_data fields of the TaxLot and Property
        State objects and make sure there are columns that point to them.
        """

        logging_info("Creating any columns for non-mapped extra data fields for organization {}".format(org))

        property_states = PropertyState.objects.filter(organization=org).all()
        taxlot_states = TaxLotState.objects.filter(organization=org).all()

        get_ed_keys = lambda state: state.extra_data.keys()

        property_keys = set(itertools.chain.from_iterable(map(get_ed_keys, property_states)))
        taxlot_keys = set(itertools.chain.from_iterable(map(get_ed_keys, taxlot_states)))

        # Iterate through each of the extra data fields associated
        # with the org's PropertyState objects and check to make sure
        # there is Column with that key name.
        for key in property_keys:
            cnt = Column.objects.filter(organization=org, column_name=key).count()

            if not cnt:
                logging_info("Missing column '{}' found in PropertyState extra_data keys".format(key))

                logging_info("Creating missing column '{}'".format(key))
                col = Column(organization=org,
                             column_name=key,
                             is_extra_data=True,
                             table_name="PropertyState")
                col.save()

        # Iterate through each of the extra data fields associated with the TaxLotStates
        for key in taxlot_keys:
            cnt = Column.objects.filter(organization=org, column_name=key).count()

            if not cnt:
                logging_info("Missing column '{}' found in TaxLotState extra_data keys.".format(key))

                logging_info("Creating missing column '{}'".format(key))

                col = Column(organization=org,
                             column_name=key,
                             is_extra_data=True,
                             table_name="TaxLotState")
                col.save()

        return

    def update_columns_based_on_mappings_file(self, org):
        """Go through each of the organization columns as reported by the
        'extradata.csv' mappings file and make sure it points to the
        table specified in that file.
        """

        logging_info("Updating columns for org {} to match that in migration mapping file.".format(org))

        taxlot_column_names = get_taxlot_columns(org)
        property_column_names = get_property_columns(org)

        found = 0
        notfound = 0

        for prop_col in property_column_names:
            qry = Column.objects.filter(organization=org, column_name=prop_col)
            cnt = qry.count()
            if cnt:
                # Update the column
                col = qry.first()
                logging_info("Setting Column '{}' to SOURCE_PROPERTY".format(col))
                col.extra_data_source = Column.SOURCE_PROPERTY
                col.save()
            else:
                col = Column(organization=org,
                             column_name=prop_col,
                             is_extra_data=True,
                             table_name="PropertyState")
                logging_info("Creating Column '{}' based on missing from mappings file".format(prop_col))
                col.save()

        for tl_col in taxlot_column_names:
            qry = Column.objects.filter(organization=org, column_name=tl_col)
            cnt = qry.count()

            if cnt:
                # Update the column
                col = qry.first()
                col.extra_data_source = Column.SOURCE_TAXLOT
                logging_info("Setting Column '{}' to SOURCE_TAXLOT".format(col))
                col.save()
            else:
                col = Column(organization=org,
                             column_name=tl_col,
                             is_extra_data=True,
                             table_name="TaxLotState")
                logging_info("Creating Column '{}' based on missing from mappings file".format(tl_col))
                col.save()

        return
