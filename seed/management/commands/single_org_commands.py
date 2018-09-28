"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from __future__ import unicode_literals

import logging

from django.core.management.base import BaseCommand

from _localtools import logging_info
from seed.models import PropertyState
from seed.models import TaxLotState

logging.basicConfig(level=logging.DEBUG)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--org', dest='organization', default=False)
        parser.add_argument('--stats', dest='stats', default=False, action="store_true")
        return

    def handle(self, *args, **options):
        logging_info("RUN  org_specific_commands with args={},kwds={}".format(args, options))
        if options['organization']:
            core_organization = map(int, options['organization'].split(","))
        else:
            core_organization = [20, 69]

        logging_info("Processing organization list: {}".format(core_organization))

        for org in core_organization:
            process_org(org)

        logging_info("END org_specific_commands")
        return


def process_org(org):
    if org == 20:
        do_process_org_20()
    elif org == 69:
        do_process_org_69()

    return


def do_process_org_69():
    print "Single Commands for org=69"
    org_pk = 69

    tax_attrs_to_clear = ["address_line_1", "city", "state", "postal_code"]
    property_attrs_to_clear = ["address_line_1", "city", "state", "postal_code"]

    for ndx, property_state in enumerate(PropertyState.objects.filter(organization_id=org_pk).all()):
        for pa in property_attrs_to_clear:
            setattr(property_state, pa, None)
            property_state.save()

    for ndx, taxlot_state in enumerate(TaxLotState.objects.filter(organization_id=org_pk).all()):
        for ta in tax_attrs_to_clear:
            setattr(taxlot_state, ta, None)
            taxlot_state.save()
    return


def do_process_org_20():
    print "Single Commands for org=20"
    count = PropertyState.objects.filter(organization_id=20).count()
    for ndx, prop in enumerate(PropertyState.objects.filter(organization_id=20).all()):
        print "Processing {}/{}".format(ndx + 1, count)

        if prop.address_line_1:
            prop.extra_data["Address 1"] = prop.address_line_1
            prop.address_line_1 = None

        if prop.address_line_2:
            prop.extra_data["Address 2"] = prop.address_line_2
            prop.address_line_2 = None

        if prop.normalized_address:
            prop.extra_data["Normalized Address"] = prop.normalized_address
            prop.normalized_address = None

        prop.save()

    for ndx, tl in enumerate(TaxLotState.objects.filter(organization_id=20).all()):
        tl.address_line_1 = None
        tl.address_line_2 = None
        tl.normalized_address = None
        tl.save()
