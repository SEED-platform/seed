# -*- coding: utf-8 -*-
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from __future__ import unicode_literals

import collections
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
        logging_info("RUN create_m2m_relatinships_organization with args={},kwds={}".format(args, options))
        if options['organization']:
            core_organization = list(map(int, options['organization'].split(",")))
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
