"""Management command to copy labels from the Old-World model that
associates labels with CanonicalBuildings to the New-World model that
associates labels with PropertyViews and with TaxLotViews.
"""

from __future__ import unicode_literals

from seed.models import CanonicalBuilding
from seed.models import Property
from seed.models import PropertyView
from seed.models import TaxLot
from seed.models import TaxLotView


from _localtools import get_core_organizations
from _localtools import logging_info
from _localtools import logging_debug

from django.core.management.base import BaseCommand
from seed.lib.superperms.orgs.models import Organization
from django.core.exceptions import ObjectDoesNotExist


class Command(BaseCommand):
        def add_arguments(self, parser):
            parser.add_argument('--org', dest='organization', default=False)

            parser.add_argument('--clear-bluesky-labels', dest='clear_bluesky_labels', default=False, action="store_true",
                                help="Delete all labels associated with all View objects")

            parser.add_argument('--labels-add-property-labels', dest='add_property_labels', default=True, action="store_true",
                                help="Create labels for PropertyView Objects")
            parser.add_argument('--labels-no-add-property-labels', dest='add_property_labels', default=True, action="store_false",
                                help="Do not create Labels to Property View Objects")

            parser.add_argument('--labels-add-taxlot-labels', dest='add_taxlot_labels', default=True, action="store_true",
                                help="Create labels on TaxLotView objects")

            parser.add_argument('--labels-no-add-taxlot-labels', dest='add_taxlot_labels', default=True, action="store_false",
                                help="Do not create labels on TaxLotView objects")
            return


        def handle(self, *args, **options):
            logging_info("RUN migrate_extradata_columns with args={},kwds={}".format(args, options))
            # Process Arguments
            if options['organization']:
                organization_ids = map(int, options['organization'].split(","))
            else:
                organization_ids = get_core_organizations()

            clear_bluesky_labels = options["clear_bluesky_labels"]

            add_property_labels = options["add_property_labels"]
            add_taxlot_labels = options["add_taxlot_labels"]

            for org_id in organization_ids:

                ##############################
                # Handle the clear case.  This is a bit inelegant the
                # way the loop on org_ids is setup.
                if clear_bluesky_labels:
                    print "Org={}: Clearing all labels on Property and TaxLot objects.".format(org_id)
                    for prop in Property.objects.filter(organization = org_id).all():
                        prop.labels.clear()
                    for tax_lot in TaxLot.objects.filter(organization = org_id).all():
                        tax_lot.labels.clear()
                    continue

                # End Clear Case
                ##############################


                print ("Org={}: Migrating Labels with settings add_property_labels={}"
                       ", add_taxlot_labels={}").format(org_id, add_property_labels, add_taxlot_labels)


                ##############################
                # Copy Property

                if add_property_labels:
                    # This is inefficient, in that it does each
                    # property/tax lot multiple times for each of it's
                    # views - but it's clear and should not be
                    # prohibitively wasteful.

                    # Alternatively you could grab the first
                    # propertyview/taxlotview for each property/taxlot
                    # and then use the state on that to populate the
                    # property/taxlot.

                    for pv in PropertyView.objects.filter(property__organization = org_id).select_related('state').all():
                        if not "prop_cb_id" in pv.state.extra_data:
                            print "Warning: key 'prop_cb_id' was not found for PropertyView={}".format(pv)
                            continue

                        cb_id = pv.state.extra_data['prop_cb_id']

                        try:
                            cb = CanonicalBuilding.objects.get(pk=cb_id)
                        except ObjectDoesNotExist, xcpt:
                            print "Warning: Canonical Building={} was not found in the DB".format(cb_id)
                            continue

                        cb_labels = cb.labels.all()
                        preexisting_pv_labels = set(map(lambda l: l.pk, pv.property.labels.all()))

                        for label in cb_labels:
                            if label.pk not in preexisting_pv_labels:
                                pv.property.labels.add(label)
                        else:
                            pv.property.save()
                #
                ##############################


                ##############################
                # Copy Tax Lot labels
                if add_taxlot_labels:
                    for tlv in TaxLotView.objects.filter(taxlot__organization = org_id).select_related('state').all():
                        if not "taxlot_cb_id" in tlv.state.extra_data:
                            print "Warning: key 'prop_cb_id' was not found for TaxLotView={}".format(tlv)
                            continue

                        cb_id = tlv.state.extra_data['taxlot_cb_id']

                        try:
                            cb = CanonicalBuilding.objects.get(pk=cb_id)
                        except ObjectDoesNotExist, xcpt:
                            print "Warning: Canonical Building={} was not found in the DB".format(cb_id)
                            continue

                        cb_labels = cb.labels.all()
                        preexisting_tlv_labels = set(map(lambda l: l.pk, tlv.taxlot.labels.all()))

                        for label in cb_labels:
                            if label.pk not in preexisting_tlv_labels:
                                tlv.taxlot.labels.add(label)
                        else:
                            tlv.taxlot.save()
                #
                ##############################

            logging_info("END migrate_extradata_columns")
            return
