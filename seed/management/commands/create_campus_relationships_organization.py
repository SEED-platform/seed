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


def find_property_associated_with_portfolio_manager_id(pm_lot_id):
    if pm_lot_id is None: return False

    result = PropertyView.objects.filter(state__building_portfolio_manager_identifier=pm_lot_id)\
                                 .first()
    if result is None: return False

    return result.property


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--org', dest='organization', default=False)
        return

    def handle(self, *args, **options):
        """Do something."""


        if options['organization']:
            core_organization = map(int, options['organization'].split(","))
        else:
            core_organization = get_core_organizations()


        for org_id in core_organization:
            # Writing loop over organizations

            org = Organization.objects.filter(pk=org_id).first()
            logging.info("Processing organization {}".format(org))

            assert org, "Organization {} not found".format(org_id)


            property_views = PropertyView.objects.filter(cycle__organization=org)\
                                                 .exclude(state__pm_parent_property_id=None)\
                                                 .exclude(state__pm_parent_property_id="Not Applicable: Standalone Property")\
                                                 .all()

            property_views = list(property_views)
            property_views.sort(key = lambda pv: pv.cycle.start)

            states = map(lambda pv: pv.state, list(property_views))

            for (pv, state) in zip(property_views, states):
                pm_parent_property_id = state.pm_parent_property_id
                if pm_parent_property_id == state.building_portfolio_manager_identifier:
                    print "Auto reference!"
                    prop = pv.property
                    prop.campus = True
                    prop.save()
                    continue

                parent_property = find_property_associated_with_portfolio_manager_id(pm_parent_property_id)
                if not parent_property:
                    print "Could not find parent property."
                    parent_property = Property(organization_id=org_id)
                    parent_property.campus = True
                    parent_property.save()

                    # Create a view and a state for the active cycle.
                    parent_property_state = PropertyState(building_portfolio_manager_identifier=pm_parent_property_id,
                                                          pm_parent_property_id=pm_parent_property_id,
                                                          property_notes="Created by campus relations migration on {}".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
                    parent_property_state.save()



                    parent_property_view = PropertyView(property = parent_property, cycle = pv.cycle, state=parent_property_state)
                    parent_property_view.save()

                    child_property = pv.property
                    child_property = child_property.parent_property = parent_property
                    child_property.save()


                else:
                    print "found campus relationship"
                    parent_property.campus = True
                    parent_property.save()

                    child_property = pv.property
                    child_property.parent_property = parent_property
                    child_property.save()

                    # Make sure the parent has a view for the same
                    # cycle as the pv in question.

                    if not PropertyView.objects.filter(property=parent_property, cycle=pv.cycle).count():

                        parent_views = PropertyView.objects.filter(property=parent_property).all()
                        parent_views = [ppv for ppv in parent_views if ppv.cycle.start <= pv.cycle.start]
                        assert len(parent_views), "This should always be true."



                        ps = parent_views[-1].state
                        ps.pk = None

                        ps.save()

                        parent_view = PropertyView(property=parent_property, cycle = pv.cycle, state = ps)
                        parent_view.save()





        return
