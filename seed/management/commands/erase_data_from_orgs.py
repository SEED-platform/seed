from __future__ import unicode_literals

from django.db import models, migrations
from django.core.management.base import BaseCommand
from seed.lib.superperms.orgs.models import Organization
from django.apps import apps
from seed.models import *
import pdb
import copy
import collections
import os
import datetime
import logging
import itertools
import csv
import StringIO
from IPython import embed
import seed.models
import numpy as np
from scipy.sparse import dok_matrix
from scipy.sparse.csgraph import connected_components
from _localtools import projection_onto_index
from _localtools import get_static_building_snapshot_tree_file
from _localtools import get_static_extradata_mapping_file
from _localtools import read_building_snapshot_tree_structure
from _localtools import get_core_organizations
from _localtools import get_node_sinks
from _localtools import find_or_create_bluesky_taxlot_associated_with_building_snapshot
from _localtools import find_or_create_bluesky_property_associated_with_building_snapshot
from _localtools import load_organization_field_mapping_for_type_exclusions
from _localtools import load_organization_field_mapping_for_type
from _localtools import load_organization_property_extra_data_mapping_exclusions
from _localtools import load_organization_taxlot_extra_data_mapping_exclusions
from _localtools import load_organization_property_field_mapping
from _localtools import load_organization_taxlot_field_mapping
from _localtools import logging_info
from _localtools import logging_debug
from _localtools import logging_warn
from _localtools import logging_error
from seed.models import TaxLotView
from seed.models import TaxLot
from seed.models import TaxLotState
from seed.models import TaxLotProperty
from seed.models import Property
from seed.models import PropertyView
from seed.models import PropertyState
from seed.models import Cycle
from _localtools import TaxLotIDValueError
from _localtools import get_id_fields
from _localtools import USE_FIRST_VALUE
from _localtools import JOIN_STRINGS
from _localtools import UNIQUE_LIST
from _localtools import aggregate_value_from_state

import re

logging.basicConfig(level=logging.DEBUG)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--org', dest='organization', default=False)
        parser.add_argument('--stats', dest='stats', default=False, action="store_true")
        return


    def handle(self, *args, **options):
        logging_info("RUN create_m2m_relatinships_organization with args={},kwds={}".format(args, options))
        if options['organization']:
            core_organization = map(int, options['organization'].split(","))
        else:
            core_organization = [20, 69]

        logging_info("Processing organization list: {}".format(core_organization))

        for org in core_organization:
            delete_data_from_org(org)

        logging_info("END create_m2m_relatinships_organization")
        return


def delete_data_from_org(org_pk):
    tax_attrs_to_clear = collections.defaultdict(list)
    property_attrs_to_clear = collections.defaultdict(list)

    tax_attrs_to_clear[69] = ["address_line_1", "city", "state", "postal_code"]
    property_attrs_to_clear[69] = ["address_line_1", "city", "state", "postal_code"]


    for ndx, property_state in enumerate(PropertyState.objects.filter(organization_id=org_pk).all()):
        for pa in property_attrs_to_clear[org_pk]:
            setattr(property_state, pa, None)
            property_state.save()

    for ndx, taxlot_state in enumerate(TaxLotState.objects.filter(organization_id=org_pk).all()):
        for ta in tax_attrs_to_clear[org_pk]:
            setattr(taxlot_state, ta, None)
            taxlot_state.save()



    return
