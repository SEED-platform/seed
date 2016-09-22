"""Management command to copy labels from the Old-World model that
associates labels with CanonicalBuildings to the New-World model that
associates labels with PropertyViews and with TaxLotViews.
"""

from __future__ import unicode_literals

from django.apps import apps
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist

from seed.models import (
    CanonicalBuilding, Property, PropertyView, TaxLot, TaxLotView
)

from _localtools import get_core_organizations
from _localtools import logging_info
from _localtools import logging_debug

PropertyLabels = apps.get_model("seed", "Property_labels")
TaxLotLabels = apps.get_model("seed", "TaxLot_labels")


class Command(BaseCommand):
        def add_arguments(self, parser):
            parser.add_argument('--org', dest='organization', default=False)

            parser.add_argument(
                '--clear-bluesky-labels', dest='clear_bluesky_labels',
                default=False, action="store_true",
                help="Delete all labels associated with all View objects"
            )

            parser.add_argument(
                '--labels-add-property-labels', dest='add_property_labels',
                default=True, action="store_true",
                help="Create labels for Property Objects"
            )
            parser.add_argument(
                '--labels-no-add-property-labels', dest='add_property_labels',
                default=True, action="store_false",
                help="Do not create Labels to Property Objects"
            )

            parser.add_argument(
                '--labels-add-taxlot-labels', dest='add_taxlot_labels',
                default=True, action="store_true",
                help="Create labels on TaxLot objects"
            )

            parser.add_argument(
                '--labels-no-add-taxlot-labels', dest='add_taxlot_labels',
                default=True, action="store_false",
                help="Do not create labels on TaxLot objects"
            )
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
                # Handle the clear case.
                if clear_bluesky_labels:
                    print "Org={}: Clearing all labels on Property and TaxLot objects.".format(org_id)
                    property_ids = Property.objects.filter(
                        organization_id=org_id
                    ).values_list('id')
                    PropertyLabels.objects.filter(
                        property_id__in=property_ids
                    ).delete()

                    taxlot_ids = TaxLot.objects.filter(
                        organization_id=org_id
                    ).values_list('id')
                    TaxLotLabels.objects.filter(
                        taxlot_id__in=taxlot_ids
                    ).delete()

                    continue

                # End Clear Case
                ##############################

                print (
                    "Org={}: Migrating Labels with settings add_property_labels={}"
                    ", add_taxlot_labels={}"
                ).format(org_id, add_property_labels, add_taxlot_labels)

                ##############################
                # Copy Property

                if add_property_labels:
                    for pv in PropertyView.objects.filter(
                        property__organization=org_id
                    ).select_related('state').all():
                        if "prop_cb_id" not in pv.state.extra_data:
                            print "Warning: key 'prop_cb_id' was not found for PropertyView={}".format(pv)
                            continue

                        cb_id = pv.state.extra_data['prop_cb_id']

                        try:
                            cb = CanonicalBuilding.objects.get(pk=cb_id)
                        except ObjectDoesNotExist:
                            print "Warning: Canonical Building={} was not found in the DB".format(cb_id)
                            continue

                        cb_labels = cb.labels.all()

                        for label in cb_labels:
                            # note: won't add a label twice,
                            pv.property.labels.add(label)

                ##############################
                # Copy Tax Lot labels

                if add_taxlot_labels:
                    for tlv in TaxLotView.objects.filter(
                            taxlot__organization=org_id
                    ).select_related('state').all():
                        if "taxlot_cb_id" not in tlv.state.extra_data:
                            print "Warning: key 'prop_cb_id' was not found for TaxLotView={}".format(tlv)
                            continue

                        cb_id = tlv.state.extra_data['taxlot_cb_id']

                        try:
                            cb = CanonicalBuilding.objects.get(pk=cb_id)
                        except ObjectDoesNotExist:
                            print "Warning: Canonical Building={} was not found in the DB".format(cb_id)
                            continue

                        cb_labels = cb.labels.all()

                        for label in cb_labels:
                            # note: won't add a label twice,
                            tlv.taxlot.labels.add(label)

                ##############################

            logging_info("END migrate_extradata_columns")
            return
