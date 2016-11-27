"""Management command to handle DC's special case
"""

from __future__ import unicode_literals

from _localtools import logging_info
from _localtools import logging_debug

from django.db.models import Q
from django.core.management.base import BaseCommand
from seed.lib.superperms.orgs.models import Organization
from django.core.exceptions import ObjectDoesNotExist
from seed.models import Cycle
from seed.models import PropertyView
from seed.models import TaxLotView
from seed.models import TaxLotProperty
import csv
import os
import re
import pdb
from IPython import embed

base_m2m_fn = "dc_junction_table.csv"
current_directory = os.path.split(__file__)[0]
DC_M2M_FN = os.path.join(current_directory, base_m2m_fn)
DC_ORG_PK=184

def processLinks(all_links):
    all_broken_links = set()

    for (pm_id, tl_list_id) in all_links:
        for tl_id in filter(lambda x: x, map(lambda x: x.strip(), re.split("[,;]", tl_list_id))):
            all_broken_links.add((pm_id, tl_id))
    return all_broken_links

class Command(BaseCommand):
    def add_arguments(self, parser):
        return

    def handle(self, *args, **options):
        logging_info("RUN migrate_dc_m2m with args={},kwds={}".format(args, options))

        dc_org = Organization.objects.get(pk=DC_ORG_PK)
        dc_cycles = Cycle.objects.filter(organization=dc_org)

        assert os.path.isfile(DC_M2M_FN), "DC Junction File '{}' not found".format(DC_M2M_FN)

        num_m2m = TaxLotProperty.objects.filter(property_view__property__organization=dc_org).count()
        logging_info("Deleting {} M2M objects for org {}".format(num_m2m, dc_org))
        TaxLotProperty.objects.filter(property_view__property__organization=dc_org).delete()

        reader = csv.reader(open(DC_M2M_FN, 'rU'))
        reader.next() # Throw away header

        pmids_taxlotids_m2m = [(y,z) for (y,z) in reader]

        all_links = set(pmids_taxlotids_m2m)

        all_links = processLinks(all_links)

        all_properties = set(map(lambda (x,y): x, all_links))
        all_taxlots = set(map(lambda (x,y): y, all_links))

        # print "-" * 30
        # print "Taxlots with len != 8"
        # for x in sorted(filter(lambda x: len(x) != 8, all_taxlots), key=len): print x
        # print "-" * 30

        found_links = set()
        found_taxlots = set()
        found_properties = set()

        logging_info("Processing {} m2m links from {} file across {} cycles.".format(len(pmids_taxlotids_m2m), DC_M2M_FN, len(dc_cycles)))

        for (ndx, (tl_id, pm_id)) in enumerate(all_links):
            if ndx % 400 == 1:
                percent_done = 100.0 * ndx / len(pmids_taxlotids_m2m)
                print "{:.2f}% done.".format(percent_done)
            # for cycle in dc_cycles:
            #     embed()
            #     combined_q_obj =  Q(state__extra_data__contains=pm_id) | Q(state__extra_data__contains='{}-{}'.format(pm_id[:4], pm_id[4:]))
            #     pdb.set_trace()
            #     pv = PropertyView.objects.filter(state__organization=dc_org,cycle=cycle).filter(combined_q_obj)


            #     tlv = TaxLotView.objects.filter(state__organization=dc_org,
            #                                     state__jurisdiction_tax_lot_id__contains=tl_id,
            #                                     cycle=cycle)

            #     if len(pv): found_properties.add(pm_id)
            #     if len(tlv): found_taxlots.add(tl_id)

            pv = pv = PropertyView.objects.filter(state__organization=dc_org).filter(state__pm_property_id__contains=pm_id)
            tlv = TaxLotView.objects.filter(state__organization=dc_org,
                                            state__jurisdiction_tax_lot_id__contains=tl_id)

            pdb.set_trace()

            if len(pv): found_properties.add(pm_id)
            if len(tlv): found_taxlots.add(tl_id)


                # if len(pv) and len(tlv):
                    # TaxLotProperty.objects.create(property_view=pv.first(),
                    #                               taxlot_view=tlv.first(),
                    #                               cycle=cycle)
                    # found_links.add((pm_id, tl_id))


        else:
            # pdb.set_trace()
            print "Found {}% of Properties - {} found, {} unfound".format(100.0 * len(found_properties) / len(all_properties), len(found_properties), len(all_properties) - len(found_properties))
            print "Found {}% of TaxLots - {} found, {} unfound".format(100.0 * len(found_taxlots) / len(all_taxlots), len(found_taxlots), len(all_taxlots) - len(found_taxlots))
            print "Found {}% of Links - {} found, {} unfound".format(100.0 * len(found_links) / len(all_links), len(found_links), len(all_links) - len(found_links))


            print "Unmatched Properties:"
            for p in sorted(all_properties - found_properties):
                print p

            print "\n" * 2
            print "Unmatched TaxLots:"
            for p in sorted(all_taxlots - found_taxlots):
                print p







        logging_info("END migrate_dc_m2m")
        return
