"""Command to go through m2m Records and assign primary/secondary.
"""

from __future__ import unicode_literals

from django.core.management.base import BaseCommand

from _localtools import get_core_organizations
from _localtools import logging_info
from _localtools import logging_debug
from seed.models import *

logging.basicConfig(level=logging.DEBUG)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--org', dest='organization', default=False)
        return

    def handle(self, *args, **options):
        """Go through organization by organization and look for m2m."""

        logging_info("RUN create_primarysecondary_taxlots with args={},kwds={}".format(args, options))

        if options['organization']:
            core_organization = map(int, options['organization'].split(","))
        else:
            core_organization = get_core_organizations()

        for org_id in core_organization:
            # Writing loop over organizations

            org = Organization.objects.filter(pk=org_id).first()
            logging_info("Processing organization {}".format(org))

            assert org, "Organization {} not found".format(org_id)

            self.assign_primarysecondary_tax_lots(org)

        logging_info("END create_primarysecondary_taxlots")
        return

    def assign_primarysecondary_tax_lots(self, org):
        for property_view in PropertyView.objects.filter(property__organization=org).all():
            logging_info("assign_primarysecondary_tax_lots for property {p}".format(p = property_view.state.pm_property_id))
            found_ct = TaxLotProperty.objects.filter(property_view=property_view).count()
            logging_info("Found {ct} TaxLotProperty".format(ct = found_ct))
            if found_ct <= 1: 
                continue            
            links = list(TaxLotProperty.objects.filter(property_view=property_view).order_by(
                'taxlot_view__state__jurisdiction_tax_lot_id').all())
            logging_info("Found {ct} linked TaxLotProperties".format(ct = len(links)))
            for ndx in xrange(1, len(links)):
                logging_info("Setting secondary for property {p} for cycle {c}:  {s}".format(p = property_view.state.pm_property_id, c = property_view.cycle.name, s = links[ndx].property_view.state.pm_property_id))
                links[ndx].primary = False
                links[ndx].save()

        return
