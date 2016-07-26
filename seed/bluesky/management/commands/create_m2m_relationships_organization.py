from __future__ import unicode_literals

from django.db import models, migrations
from django.core.management.base import BaseCommand
from seed.lib.superperms.orgs.models import Organization
from django.apps import apps
from seed.bluesky.models import *
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
import seed.bluesky.models
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
from seed.bluesky.models import TaxLotView
from seed.bluesky.models import TaxLot
from seed.bluesky.models import TaxLotState
from seed.bluesky.models import TaxLotProperty
from seed.bluesky.models import Property
from seed.bluesky.models import PropertyView
from seed.bluesky.models import PropertyState
from seed.bluesky.models import Cycle
import re

logging.basicConfig(level=logging.DEBUG)

class TaxLotIDValueError(ValueError):
    def __init__(self, original_string, field = None):
        super(TaxLotIDValueError, self).__init__("Invalid id string found: {}".format(original_string))
        self.invalid_field = field
        self.original_string = original_string
        return

def valid_id(s):
    if not s: return True

    #pattern = r"[\w\-\s]+$"
    if len(s) == 1:
        #trying to do the case where the string is only one character was too complicated
        #so just do it separate for now
        pattern = r"\w"
    else:
        #Rules for individual field:
        #Must start and end with alphanumeric (\w)
        #May have any combination of whitespace, hyphens ("-") and alphanumerics in the middle
        pattern = r"\w[\w\-\s]*\w$"
    return re.match(pattern, s)

def sanitize_delimiters(s, delimiter_to_use, other_delimiters):
    """Replace all delimiters with preferred delimiter"""
    for d in other_delimiters:
        s = s.replace(d, delimiter_to_use)
    return s

def check_delimiter_sanity(check_str, delimiters):
    """Ensure that only one kind of delimiter is used."""
    return map(lambda delim: delim in check_str, delimiters).count(True) <= 1

def get_id_fields(parse_string):
    """Parse a string into a list of taxlots.

    Raises an exception if string does not match
    """

    if parse_string is None: raise TaxLotIDValueError(parse_string)

    #The id field can use any of several delimiters so reduce it to just one
    #delimiter first to make things easier
    delimiter_to_use = ","
    other_delimiters = [";", ":"]

    # if not check_delimiter_sanity(parse_string, [delimiter_to_use] + other_delimiters):
    #     raise TaxLotIDValueError(parse_string)


    cleaned_str = sanitize_delimiters(parse_string, delimiter_to_use, other_delimiters)

    #If there is nothing in the string return an empty list
    if not len(cleaned_str.strip()):
        return []

    fields = cleaned_str.split(delimiter_to_use)
    #leading and trailing whitespace is part of the delimiter and not the ids
    #so remove it here before additional processing
    fields = [f.strip() for f in fields]

    # A list like "a;b;" is always interperet as a two element list
    # A list like a;;b is interpreted as a two element list
    # A list like a;;b; is interpreted as a two element list
    if fields and not fields[-1]: fields.pop()

    for field in fields:
        if not valid_id(field):
            raise TaxLotIDValueError(parse_string, field)

    return fields


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--org', dest='organization', default=False)
        parser.add_argument('--stats', dest='stats', default=False, action="store_true")
        return


    def handle(self, *args, **options):
        if options['organization']:
            core_organization = map(int, options['organization'].split(","))
        else:
            core_organization = get_core_organizations()

        logging.info("Processing organization list: {}".format(core_organization))

        if options['stats']:
            for org_id in core_organization:
                self.display_stats(org_id)
                return

        for org_id in core_organization:
            self.split_taxlots_into_m2m_relationships(org_id)

        # At the end run two checks:


        # Go through the tax Lots, collect any that are left, make
        # sure they aren't a part of any m2m entities.
        for view in TaxLotView.objects.filter(taxlot__organization_id=org_id).all():
            try:
                taxlot_field_list = get_id_fields(view.state.jurisdiction_taxlot_identifier)
                if len(taxlot_field_list) > 1:
                    print "Danger - tax lot '{}' still exists.".format(view.state.jurisdiction_taxlot_identifier)
            except TaxLotIDValueError, e:
                continue


        return

    def split_taxlots_into_m2m_relationships(self, org_id):
        org = Organization.objects.get(pk=org_id)
        print "==== Splitting for organization {} - {}".format(org_id, org.name)

        created_tax_lots = collections.defaultdict(lambda : False)

        for m2m in itertools.chain(TaxLotProperty.objects.filter(property_view__property__organization=org).all(),
                                   TaxLotProperty.objects.filter(taxlot_view__taxlot__organization=org).all()):
            jurisdiction_taxlot_identifier = m2m.taxlot_view.state.jurisdiction_taxlot_identifier
            taxlot_id_list = []
            try:
                taxlot_id_list = get_id_fields(m2m.taxlot_view.state.jurisdiction_taxlot_identifier)
                print taxlot_id_list # HOHO
            except TaxLotIDValueError, e:
                print e # HOHO
                continue


            if len(taxlot_id_list) <= 1: continue

            original_taxlot_view = m2m.taxlot_view
            # Some have duplicates
            for taxlot_id in set(taxlot_id_list):
                print "Break up tax lot {} to {} for cycle {}".format(jurisdiction_taxlot_identifier, taxlot_id_list, m2m.cycle)
                # Take tax lot and create a taxlot, a taxlot view, and a taxlot state.
                # taxlot state, and an m2m for the view and installs each.

                # Check to see if the tax lot exists

                matching_views_qry = TaxLotView.objects.filter(taxlot__organization=org, state__jurisdiction_taxlot_identifier=taxlot_id)
                if matching_views_qry.count():
                    tax_lot = matching_views_qry.first().taxlot

                    # FIXME: Yuck! Refactor me please!
                    created_tax_lots[taxlot_id] = tax_lot

                    # Apparently this is how Django clones things?
                    taxlot_state = original_taxlot_view.state
                    taxlot_state.pk = None
                    taxlot_state.jurisdiction_taxlot_identifier = taxlot_id
                    taxlot_state.save()

                else:
                    tl = TaxLot(organization=m2m.taxlot_view.taxlot.organization)
                    tl.save()
                    created_tax_lots[taxlot_id] = tl

                    # Apparently this is how Django clones things?
                    taxlot_state = original_taxlot_view.state
                    taxlot_state.pk = None
                    taxlot_state.jurisdiction_taxlot_identifier = taxlot_id
                    taxlot_state.save()




                # Check and see if the Tax Lot View exists
                qry = TaxLotView.objects.filter(taxlot = created_tax_lots[taxlot_id], cycle = m2m.cycle)
                if qry.count():
                    taxlotview = qry.first()
                    taxlotview.state = taxlot_state
                    taxlotview.save()
                else:
                    taxlotview = TaxLotView(taxlot = created_tax_lots[taxlot_id], cycle = m2m.cycle, state = taxlot_state)
                    # Clone the state from above
                    taxlotview.save()


                TaxLotProperty.objects.get_or_create(property_view = m2m.property_view, taxlot_view = taxlotview, cycle = m2m.cycle)


            else:
                # The existing TaxLotView and m2m is deleted.
                tl_view = m2m.taxlot_view
                m2m.delete()
                tl_view.delete()
                pass

            # Go through each view, find all it's tax lot ids and make sure they don't look like lists of many things.
            print "{} => {}".format(jurisdiction_taxlot_identifier, taxlot_id_list)


        # Go through the tax Lots, collect any that are left, make
        # sure they aren't a part of any m2m entities.
        for original_taxlot_view in TaxLotView.objects.filter(taxlot__organization=org).all():
            try:

                jurisdiction_taxlot_identifier = original_taxlot_view.state.jurisdiction_taxlot_identifier
                taxlot_id_list = get_id_fields(jurisdiction_taxlot_identifier)
                if len(taxlot_id_list) <= 1: continue
                assert TaxLotProperty.objects.filter(taxlot_view = original_taxlot_view).count() == 0, "Tax Lot should have been broken up already."

                # Some have duplicates
                for taxlot_id in set(taxlot_id_list):
                    print "Break up tax lot {} to {} for cycle {}".format(jurisdiction_taxlot_identifier, taxlot_id_list, m2m.cycle)
                    # Take tax lot and create a taxlot, a taxlot view, and a taxlot state.
                    # taxlot state, and an m2m for the view and installs each.

                    matching_views_qry = TaxLotView.objects.filter(taxlot__organization=org, state__jurisdiction_taxlot_identifier=taxlot_id)
                    if matching_views_qry.count():
                        taxlot = matching_views_qry.first().taxlot

                        if TaxLotView.objects.filter(taxlot = taxlot, cycle = original_taxlot_view.cycle).count() == 0:
                            taxlot_state = original_taxlot_view.state
                            taxlot_state.pk = None
                            taxlot_state.jurisdiction_taxlot_identifier = taxlot_id
                            taxlot_state.save()

                            tlv = TaxLotView(taxlot = taxlot, cycle = original_taxlot_view.cycle, state = taxlot_state)
                            tlv.save()

                    else:
                        tl = TaxLot(organization=original_taxlot_view.taxlot.organization)
                        tl.save()
                        created_tax_lots[taxlot_id] = tl

                        # Apparently this is how Django clones things?
                        taxlot_state = original_taxlot_view.state
                        taxlot_state.pk = None
                        taxlot_state.jurisdiction_taxlot_identifier = taxlot_id
                        taxlot_state.save()

                        tlv = TaxLotView(taxlot = tl, cycle = original_taxlot_view.cycle, state = taxlot_state)
                        tlv.save()
                else:
                    original_taxlot_view.delete()


            except TaxLotIDValueError, e:
                continue


        # Go through and delete any orphaned Tax Lots with no Views
        for taxlot in TaxLot.objects.filter(organization_id=org_id).all():
            if TaxLotView.objects.filter(taxlot=taxlot).count() == 0:
                print "Removing empty taxlot."
                taxlot.delete()

        return


    def display_stats(self, org_id):
        org = Organization.objects.get(pk=org_id)

        logging.info("##########  PROCESSING ORGANIZATION {} - {} #################".format(org.id, org.name))
        singleton_count = 0
        malformed_count = 0
        multiple_count = 0
        invalid_strings = []

        base_query = TaxLotProperty.objects.filter(property_view__property__organization=org)

        for m2m in base_query.all():
            tax_lot_id = m2m.taxlot_view.state.jurisdiction_taxlot_identifier

            try:
                fields = get_id_fields(tax_lot_id)
                if len(fields) > 1:
                    logging.info("Possible match: {}".format(tax_lot_id))
                    multiple_count += 1
                else:
                    singleton_count += 1
            except TaxLotIDValueError, e:
                malformed_count += 1
                invalid_strings.append(e.original_string)

        logging.info("Processing {} total tax lots".format(int(base_query.count())))
        logging.info("{} plain old tax lots.".format(singleton_count))
        logging.info("{} malformed lots.".format(malformed_count))
        logging.info("{} multiple.".format(multiple_count))

        logging.info("=====  Malformed =====")
        for (ndx, major_malfunction) in enumerate(sorted(set(invalid_strings))):
            logging.info("   {}: {}".format(ndx, major_malfunction))
