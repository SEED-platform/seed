# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging
from IPython import embed

from seed.data_importer import tasks
from seed.data_importer.tests.util import (
    DataMappingBaseTestCase,
    FAKE_EXTRA_DATA,
    FAKE_MAPPINGS,
    FAKE_ROW,
)

import datetime
from django.core.files import File
from django.test import TestCase
import logging
import os.path
from seed.models import (
    Column,
    Property,
    PropertyState,
    PropertyView,
    TaxLot,
    TaxLotState,
    TaxLotProperty,
    TaxLotView,
    DATA_STATE_IMPORT,
    DATA_STATE_MAPPING,
    ASSESSED_RAW,
)

from seed.models import (
    ColumnMapping,
    Cycle,
    PropertyState,
)

from seed.data_importer.models import ImportFile, ImportRecord
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization, OrganizationUser

logger = logging.getLogger(__name__)


class TestCaseRobinDemo(DataMappingBaseTestCase):

    def set_up(self, import_file_source_type):
        """Override the base in DataMappingBaseTestCase."""

        # default_values
        import_file_is_espm = getattr(self, 'import_file_is_espm', True)
        import_file_data_state = getattr(self, 'import_file_data_state', DATA_STATE_IMPORT)

        user = User.objects.create(username='test')
        org = Organization.objects.create()

        cycle, _ = Cycle.objects.get_or_create(
            name=u'Test Hack Cycle 2015',
            organization=org,
            start=datetime.datetime(2015, 1, 1),
            end=datetime.datetime(2015, 12, 31),
        )

        # Create an org user
        OrganizationUser.objects.create(user=user, organization=org)

        import_record_1 = ImportRecord.objects.create(
            owner=user, last_modified_by=user, super_organization=org
        )
        import_file_1 = ImportFile.objects.create(import_record=import_record_1,
                                                  cycle=cycle)

        import_record_2 = ImportRecord.objects.create(
            owner=user, last_modified_by=user, super_organization=org
        )
        import_file_2 = ImportFile.objects.create(import_record=import_record_2,
                                                  cycle=cycle)

        import_file_1.is_espm = import_file_is_espm
        import_file_1.source_type = import_file_source_type
        import_file_1.data_state = import_file_data_state
        import_file_1.save()

        import_file_2.is_espm = import_file_is_espm
        import_file_2.source_type = import_file_source_type
        import_file_2.data_state = import_file_data_state
        import_file_2.save()

        return user, org, import_file_1, import_record_1, import_file_2, import_record_2, cycle

    def setUp(self):
        property_filename = getattr(self, 'filename', 'example-data-properties-V2-original-noID.xlsx')
        tax_lot_filename = getattr(self, 'filename', 'example-data-taxlots-V2-original-noID.xlsx')
        import_file_source_type = ASSESSED_RAW
        self.fake_portfolio_mappings = FAKE_MAPPINGS['portfolio']
        self.fake_taxlot_mappings = FAKE_MAPPINGS['taxlot']
        self.fake_extra_data = FAKE_EXTRA_DATA
        self.fake_row = FAKE_ROW
        selfvars = self.set_up(import_file_source_type)

        (self.user,
         self.org,
         self.import_file_property,
         self.import_record_property,
         self.import_file_tax_lot,
         self.import_record_tax_lot,
         self.cycle) = selfvars

        self.import_file_tax_lot = self.load_import_file_file(tax_lot_filename, self.import_file_tax_lot)
        self.import_file_property = self.load_import_file_file(property_filename, self.import_file_property)

    def test_robin_demo(self):
        """ Robin's demo files """

        tasks._save_raw_data(self.import_file_tax_lot.pk, 'fake_cache_key', 1)
        Column.create_mappings(self.fake_taxlot_mappings, self.org, self.user)
        Column.create_mappings(self.fake_portfolio_mappings, self.org, self.user)
        tasks.map_data(self.import_file_tax_lot.pk)

        # self.assertEqual(len(ps), 12)

        # Check to make sure the taxlots were imported
        ts = TaxLotState.objects.filter(
            data_state=DATA_STATE_MAPPING,
            organization=self.org,
            import_file=self.import_file_tax_lot,
        )

        ps = PropertyState.objects.filter(
            data_state=DATA_STATE_MAPPING,
            organization=self.org,
            import_file=self.import_file_property,
        )

        self.assertEqual(len(ps), 0)
        self.assertEqual(len(ts), 9)

        tasks.match_buildings(self.import_file_tax_lot.id, self.user.id)

        # Check a single case of the taxlotstate
        self.assertEqual(TaxLotState.objects.filter(address_line_1='050 Willow Ave SE').count(), 1)
        self.assertEqual(TaxLotView.objects.filter(state__address_line_1='050 Willow Ave SE').count(), 1)



        # Import the property data
        tasks._save_raw_data(self.import_file_property.pk, 'fake_cache_key', 1)
        tasks.map_data(self.import_file_property.pk)

        ts = TaxLotState.objects.filter(
            # data_state=DATA_STATE_MAPPING,
            organization=self.org,
            import_file=self.import_file_tax_lot,
        )

        ps = PropertyState.objects.filter(
            data_state=DATA_STATE_MAPPING,
            organization=self.org,
            import_file=self.import_file_property,
        )

        self.assertEqual(len(ts), 9)
        self.assertEqual(len(ps), 12)

        tasks.match_buildings(self.import_file_property.id, self.user.id)

        ps = PropertyState.objects.filter(
            data_state=DATA_STATE_MAPPING,
            organization=self.org,
            import_file=self.import_file_property,
        )

        self.assertEqual(len(ps), 0)

        ps = PropertyView.objects.filter(
            state__organization=self.org)

        self.assertEqual(len(ps), 12)

        # self.assertEqual(ts.jurisdiction_tax_lot_id, '1552813')
        # self.assertEqual(ts.address_line_1, None)
        # self.assertEqual(ts.extra_data["extra_data_2"], 1)

        # # Check a single case of the propertystate
        # ps = PropertyState.objects.filter(pm_property_id='2264')
        # self.assertEqual(len(ps), 1)
        # ps = ps.first()
        # self.assertEqual(ps.pm_property_id, '2264')
        # self.assertEqual(ps.address_line_1, '50 Willow Ave SE')
        # self.assertEqual(ps.extra_data["extra_data_1"], 'a')
        # self.assertEqual('extra_data_2' in ps.extra_data.keys(), False)



        # ------ TEMP CODE ------
        # Manually promote the properties
        # pv = ps.promote(self.cycle)
        # tlv = ts.promote(self.cycle)

        # # Check the count of the canonical buildings
        # from django.db.models.query import QuerySet
        # ps = tasks.list_canonical_property_states(self.org)
        # self.assertTrue(isinstance(ps, QuerySet))
        # self.assertEqual(len(ps), 1)

        # Manually pair up the ts and ps until the match/pair properties works
        # TaxLotProperty.objects.create(cycle=self.cycle, property_view=pv, taxlot_view=tlv)
        # ------ END TEMP CODE ------

        # make sure the the property only has one tax lot and vice versa
        # ts = TaxLotState.objects.filter(jurisdiction_tax_lot_id='1552813').first()
        # pv = PropertyView.objects.filter(state__pm_property_id='2264', cycle=self.cycle).first()
        # tax_lots = pv.tax_lot_states()
        # self.assertEqual(len(tax_lots), 1)
        # tlv = tax_lots[0]
        # self.assertEqual(ts, tlv)

        # ps = PropertyState.objects.filter(pm_property_id='2264').first()
        # tlv = TaxLotView.objects.filter(state__jurisdiction_tax_lot_id='1552813',
        #                                 cycle=self.cycle).first()
        # properties = tlv.property_states()
        # self.assertEqual(len(properties), 1)
        # prop_state = properties[0]
        # self.assertEqual(ps, prop_state)

        # for p in ps:
        #     pp(p)

        # tasks.match_buildings(self.import_file.id, self.user.id)

        self.assertEqual(TaxLot.objects.count(), 10)
        self.assertEqual(Property.objects.count(), 10)  # Two properties match on custom_id_1 for 7 and 9

        # qry = PropertyView.objects.filter(state__custom_id_1='7')
        # self.assertEqual(qry.count(), 1)

        # state = qry.first().state

        # self.assertEqual(state.address_line_1, "20 Tenth Street")
        # self.assertEqual(state.property_name, "Grange Hall")

        # M2M Matching

        # # Promote 5 of these to views to test the remaining code
        # promote_mes = PropertyState.objects.filter(
        #     data_state=DATA_STATE_MAPPING,
        #     super_organization=self.fake_org)[:5]
        # for promote_me in promote_mes:
        #     promote_me.promote(cycle)
        #
        # ps = tasks.list_canonical_property_states(self.fake_org)
        # from django.db.models.query import QuerySet
        # self.assertTrue(isinstance(ps, QuerySet))
        # logger.debug("There are %s properties" % len(ps))
        # for p in ps:
        #     print p
        #
        # self.assertEqual(len(ps), 5)
        # self.assertEqual(ps[0].address_line_1, '1211 Bryant Street')
        # self.assertEqual(ps[4].address_line_1, '1031 Ellis Lane')

        # tasks.match_buildings(self.import_file.pk, self.fake_user.pk)

        # self.assertEqual(result.property_name, snapshot.property_name)
        # self.assertEqual(result.property_name, new_snapshot.property_name)
        # # Since these two buildings share a common ID, we match that way.
        # # self.assertEqual(result.confidence, 0.9)
        # self.assertEqual(
        #     sorted([r.pk for r in result.parents.all()]),
        #     sorted([new_snapshot.pk, snapshot.pk])
        # )
        # self.assertGreater(AuditLog.objects.count(), 0)
        # self.assertEqual(
        #     AuditLog.objects.first().action_note,
        #     'System matched building ID.'
        # )
