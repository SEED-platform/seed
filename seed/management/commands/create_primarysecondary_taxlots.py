"""Command to go through m2m Records and assign primary/secondary.
"""

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

logging.basicConfig(level=logging.DEBUG)

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--org', dest='organization', default=False)
        return

    def handle(self, *args, **options):
        """Go through organization by organization and look for m2m."""

        if options['organization']:
            core_organization = map(int, options['organization'].split(","))
        else:
            core_organization = get_core_organizations()


        for org_id in core_organization:
            # Writing loop over organizations

            org = Organization.objects.filter(pk=org_id).first()
            logging.info("Processing organization {}".format(org))

            assert org, "Organization {} not found".format(org_id)

            self.assign_primarysecondary_tax_lots(org)

        return


    def assign_primarysecondary_tax_lots(self, org):
        for property_view in PropertyView.objects.filter(property__organization=org).all():
            if TaxLotProperty.objects.filter(property_view=property_view).count() <= 1: continue

            links = list(TaxLotProperty.objects.filter(property_view = property_view).order_by('taxlotview__state__jurisdiction_taxlot_identifier').all())

            for ndx in xrange(1, len(links)):
                print "Setting secondary"
                links[ndx].primary = False
                links[ndx].save()

        return
