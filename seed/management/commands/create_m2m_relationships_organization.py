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
            core_organization = get_core_organizations()

        logging_info("Processing organization list: {}".format(core_organization))

        if options['stats']:
            for org_id in core_organization:
                self.display_stats(org_id)
                return

        org_taxlot_splitdata_rules = collections.defaultdict(lambda : (UNIQUE_LIST, ("jurisdiction_tax_lot_id",)))
        org_taxlot_splitdata_rules[20] = (UNIQUE_LIST, ("jurisdiction_tax_lot_id", "extra_data/Philadelphia Building ID",))

        for org_id in core_organization:
            self.split_taxlots_into_m2m_relationships(org_id, org_taxlot_splitdata_rules)

        # At the end run two checks:

        # Go through the tax Lots, collect any that are left, make
        # sure they aren't a part of any m2m entities.
        for view in TaxLotView.objects.filter(taxlot__organization_id=org_id).all():
            try:
                # pdb.set_trace()
                # aggregate_value_from_state(view.state, org_taxlot_split_extra[org_id])

                taxlot_field_list = get_id_fields(view.state.jurisdiction_tax_lot_id)
                if len(taxlot_field_list) > 1:
                    logging_warn("Danger - tax lot '{}' still exists.".format(view.state.jurisdiction_tax_lot_id))
            except TaxLotIDValueError, e:
                continue

        logging_info("END create_m2m_relatinships_organization")
        return

    def split_taxlots_into_m2m_relationships(self, org_id, org_rules_map):
        org = Organization.objects.get(pk=org_id)
        logging_info("Splitting tax lot lists for organization {}/{}".format(org_id, org.name))

        created_tax_lots = collections.defaultdict(lambda : False)

        for m2m in itertools.chain(TaxLotProperty.objects.filter(property_view__property__organization=org).all(),
                                   TaxLotProperty.objects.filter(taxlot_view__taxlot__organization=org).all()):
            # aggregate_value_from_state(view.state, org_rules_map[org_id])
            
            # In some cases something in this chain of db calls in m2m.taxlot_view.state.jurisdiction_tax_lot_id
            #  something is missing.  Log it and continue.
            try:
                jurisdiction_tax_lot_id = m2m.taxlot_view.state.jurisdiction_tax_lot_id
            except Exception as e:                
                logging_error("Error splitting taxlotproperty {t} into m2m:  {e}".format(t = m2m, e = e))
                continue
            logging_info("Starting to do m2m for jurisdiction_tax_lot_id {id}".format(id = jurisdiction_tax_lot_id))
                
            taxlot_id_list = []
            try:
                taxlot_id_list = get_id_fields(m2m.taxlot_view.state.jurisdiction_tax_lot_id)
                _log.info("Found taxlot_id_list: {l}".format(l = taxlot_id_list))
            except TaxLotIDValueError, e:
                logging_warn(e)
                continue

            if len(taxlot_id_list) <= 1: continue
            logging_info("Tax lot view {} w/ tax_lot id {} was split to {} elements: {}".format(m2m.taxlot_view.pk, m2m.taxlot_view.state.jurisdiction_tax_lot_id,
                                                                                                len(taxlot_id_list), taxlot_id_list))

            original_taxlot_view = m2m.taxlot_view

            # Some have duplicates
            for tax_lot_id in set(taxlot_id_list):
                logging_info("Break up tax lot {} to {} for cycle {}".format(tax_lot_id, taxlot_id_list, m2m.cycle))
                # Take tax lot and create a taxlot, a taxlot view, and a taxlot state.
                # taxlot state, and an m2m for the view and installs each.

                # Check to see if the tax lot exists

                matching_views_qry = TaxLotView.objects.filter(taxlot__organization=org, state__jurisdiction_tax_lot_id=tax_lot_id)
                matching_views_ct = matching_views_qry.count()
                logging_info("Found {ct} matching views".format(ct = matching_views_ct))
                if matching_views_qry.count():                    
                    tax_lot = matching_views_qry.first().taxlot
                    state = matching_views_qry.first().state
                    logging_info("Found matching taxlotviews.  First is jurisdiction_tax_lot_id {id}".format(id = state.jurisdiction_tax_lot_id))
                    # FIXME: Yuck! Refactor me please!
                    created_tax_lots[tax_lot_id] = tax_lot

                    logging_info("Setting taxlot_state to jurisdiction_tax_lot_id {id}".format(id = original_taxlot_view.state.jurisdiction_tax_lot_id))
                    # Apparently this is how Django clones things?
                    taxlot_state = original_taxlot_view.state
                    taxlot_state.pk = None
                    taxlot_state.jurisdiction_tax_lot_id = tax_lot_id
                    logging_info("Setting taxlot_state.jurisdiction_tax_lot_id = {id}".format(id = tax_lot_id))
                    taxlot_state.save()

                else:
                    logging_info("No match, make a new TaxLot")
                    tl = TaxLot(organization=m2m.taxlot_view.taxlot.organization)
                    tl.save()
                    created_tax_lots[tax_lot_id] = tl

                    logging_info("Setting taxlot_state to jurisdiction_tax_lot_id {id}".format(id = original_taxlot_view.state.jurisdiction_tax_lot_id))
                    # Apparently this is how Django clones things?
                    taxlot_state = original_taxlot_view.state
                    taxlot_state.pk = None
                    taxlot_state.jurisdiction_tax_lot_id = tax_lot_id
                    logging_info("Setting taxlot_state.jurisdiction_tax_lot_id = {id}".format(id = tax_lot_id))
                    taxlot_state.save()




                # Check and see if the Tax Lot View exists
                qry = TaxLotView.objects.filter(taxlot = created_tax_lots[tax_lot_id], cycle = m2m.cycle)
                taxlotview_ct = qry.count()
                logging_info("Found {ct} matching taxlotviews".format(ct = taxlotview_ct))
                if taxlotview_ct:
                    taxlotview = qry.first()
                    logging_debug("Setting the state of {v} to {s}".format(v = taxlotview.state.jurisdiction_tax_lot_id, s = taxlot_state.jurisdiction_tax_lot_id))
                    taxlotview.state = taxlot_state                    
                    taxlotview.save()
                else:
                    logging_debug("Creating a new TaxLotView with cycle {c} and state {s}".format(c = m2m.cycle.name, s = taxlot_state.jurisdiction_tax_lot_id))
                    taxlotview = TaxLotView(taxlot = created_tax_lots[tax_lot_id], cycle = m2m.cycle, state = taxlot_state)
                    # Clone the state from above
                    taxlotview.save()


                logging_debug("TaxLotProperty.objects.get_or_create with pm_id {pm}, jurisdiction_id = {j}, cycle = {c}".format(pm = m2m.property_view.state.pm_property_id, j = taxlotview.state.jurisdiction_tax_lot_id, c = m2m.cycle.name))
                TaxLotProperty.objects.get_or_create(property_view = m2m.property_view, taxlot_view = taxlotview, cycle = m2m.cycle)


            else:
                # The existing TaxLotView and m2m is deleted.
                logging_debug("Deleting existing TaxLotView pm {pm}, jurisdiction {j}".format(pm = m2m.property_view.state.pm_property_id, j = m2m.taxlot_view.state.jurisdiction_tax_lot_id))
                tl_view = m2m.taxlot_view
                m2m.delete()
                tl_view.delete()
                pass

            # Go through each view, find all it's tax lot ids and make sure they don't look like lists of many things.
            logging_info("{} => {}".format(jurisdiction_tax_lot_id, taxlot_id_list))


        # Go through the tax Lots, collect any that are left, make
        # sure they aren't a part of any m2m entities.
        for original_taxlot_view in TaxLotView.objects.filter(taxlot__organization=org).all():
            logging_debug("Trying original_taxlot_view jurisdiction {j}".format(j = original_taxlot_view.state.jurisdiction_tax_lot_id))
            try:

                jurisdiction_tax_lot_id = original_taxlot_view.state.jurisdiction_tax_lot_id
                taxlot_id_list = get_id_fields(jurisdiction_tax_lot_id)
                logging_debug("Found taxlot_id_list with {ct} items.  {l}".format(ct = len(taxlot_id_list), l = taxlot_id_list))
                if len(taxlot_id_list) <= 1: continue
                assert TaxLotProperty.objects.filter(taxlot_view = original_taxlot_view).count() == 0, "Tax Lot should have been broken up already."
                if TaxLotProperty.objects.filter(taxlot_view = original_taxlot_view).count() != 0:
                    logging_debug("Tax Lot should have been broken up already.")
                # Some have duplicates
                for taxlot_id in set(taxlot_id_list):
                    logging_info("Break up tax lot {} to {} for cycle {}".format(jurisdiction_tax_lot_id, taxlot_id_list, m2m.cycle))
                    # Take tax lot and create a taxlot, a taxlot view, and a taxlot state.
                    # taxlot state, and an m2m for the view and installs each.

                    matching_views_qry = TaxLotView.objects.filter(taxlot__organization=org, state__jurisdiction_tax_lot_id=taxlot_id)
                    matching_views_ct = matching_views_qry.count()
                    logging_debug("Found {ct} matching views".format(ct = matching_views_ct))
                    if matching_views_ct:
                        taxlot = matching_views_qry.first().taxlot
                        taxlotview_ct = TaxLotView.objects.filter(taxlot = taxlot, cycle = original_taxlot_view.cycle).count()
                        logging_debug("Found {ct} taxlotviews".format(ct = taxlotview_ct))
                        if taxlotview_ct == 0:
                            taxlot_state = original_taxlot_view.state
                            taxlot_state.pk = None
                            taxlot_state.jurisdiction_tax_lot_id = taxlot_id
                            logging_debug("Creating a copy of the original taxlot_view's state with jurisdiction id {j}".format(j = taxlot_id))
                            taxlot_state.save()
                            logging_debug("Creating a new TaxLotView")
                            tlv = TaxLotView(taxlot = taxlot, cycle = original_taxlot_view.cycle, state = taxlot_state)
                            tlv.save()

                    else:
                        logging_debug("Creating a new TaxLot")
                        tl = TaxLot(organization=original_taxlot_view.taxlot.organization)
                        tl.save()
                        logging_debug("Adding new taxlot to created_tax_lots at index {i}".format(i = taxlot_id))
                        created_tax_lots[taxlot_id] = tl

                        # Apparently this is how Django clones things?
                        taxlot_state = original_taxlot_view.state
                        taxlot_state.pk = None
                        taxlot_state.jurisdiction_tax_lot_id = taxlot_id
                        logging_debug("Creating a copy of the original taxlot_view's state with jurisdiction id {j}".format(j = taxlot_id))
                        taxlot_state.save()
                        logging_debug("Creating a new TaxLotView")
                        tlv = TaxLotView(taxlot = tl, cycle = original_taxlot_view.cycle, state = taxlot_state)
                        tlv.save()
                else:
                    logging_debug("Deleting original taxlot_view's with jurisdiction id {j}".format(j = original_taxlot_view.state.jurisdiction_tax_lot_id))
                    original_taxlot_view.delete()


            except TaxLotIDValueError, e:
                continue


        # Go through and delete any orphaned Tax Lots with no Views
        for taxlot in TaxLot.objects.filter(organization_id=org_id).all():
            if TaxLotView.objects.filter(taxlot=taxlot).count() == 0:
                logging_info("Removing empty taxlot.")
                taxlot.delete()

        return


    def display_stats(self, org_id):
        org = Organization.objects.get(pk=org_id)

        logging_info("##########  PROCESSING ORGANIZATION {} - {} #################".format(org.id, org.name))
        singleton_count = 0
        malformed_count = 0
        multiple_count = 0
        invalid_strings = []

        base_query = TaxLotProperty.objects.filter(property_view__property__organization=org)

        for m2m in base_query.all():
            tax_lot_id = m2m.taxlot_view.state.jurisdiction_tax_lot_id

            try:
                fields = get_id_fields(tax_lot_id)
                if len(fields) > 1:
                    logging_info("Possible match: {}".format(tax_lot_id))
                    multiple_count += 1
                else:
                    singleton_count += 1
            except TaxLotIDValueError, e:
                malformed_count += 1
                invalid_strings.append(e.original_string)

        logging_info("Processing {} total tax lots".format(int(base_query.count())))
        logging_info("{} plain old tax lots.".format(singleton_count))
        logging_info("{} malformed lots.".format(malformed_count))
        logging_info("{} multiple.".format(multiple_count))

        logging_info("=====  Malformed =====")
        for (ndx, major_malfunction) in enumerate(sorted(set(invalid_strings))):
            logging_info("   {}: {}".format(ndx, major_malfunction))
