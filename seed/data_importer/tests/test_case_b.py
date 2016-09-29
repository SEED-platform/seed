# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging

from seed.data_importer import tasks
from seed.data_importer.tests.util import (
    DataMappingBaseTestCase,
    FAKE_EXTRA_DATA,
    FAKE_MAPPINGS,
    FAKE_ROW,
)
from seed.models import (
    Column,
    PropertyState,
    PropertyView,
    TaxLotState,
    TaxLotProperty,
    TaxLotView,
    DATA_STATE_MAPPING,
    ASSESSED_RAW,
)

logger = logging.getLogger(__name__)


class TestCaseB(DataMappingBaseTestCase):

    def setUp(self):
        filename = getattr(self, 'filename', 'example-data-properties.xlsx')
        import_file_source_type = ASSESSED_RAW
        self.fake_mappings = FAKE_MAPPINGS['portfolio']
        self.fake_extra_data = FAKE_EXTRA_DATA
        self.fake_row = FAKE_ROW
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        self.import_file = self.load_import_file_file(filename, self.import_file)
        tasks._save_raw_data(self.import_file.pk, 'fake_cache_key', 1)
        Column.create_mappings(self.fake_mappings, self.org, self.user)
        tasks.map_data(self.import_file.pk)

    def test_match_buildings(self):
        """ case B (many property <-> one tax lot) """
        tasks._save_raw_data(self.import_file.pk, 'fake_cache_key', 1)
        Column.create_mappings(self.fake_mappings, self.org, self.user)
        tasks.map_data(self.import_file.pk)

        # Check to make sure all the properties imported
        ps = PropertyState.objects.filter(
            data_state=DATA_STATE_MAPPING,
            organization=self.org,
            import_file=self.import_file,
        )
        self.assertEqual(len(ps), 12)

        # Check to make sure the taxlots were imported
        ts = TaxLotState.objects.filter(
            data_state=DATA_STATE_MAPPING,
            organization=self.org,
            import_file=self.import_file,
        )
        self.assertEqual(len(ts), 10)  # there are only 10 unique tax lots in the test file once splitting on delimiters # noqa

        # tasks.match_buildings(self.import_file.id, self.user.id)
        # tasks.pair_buildings(self.import_file.id, self.user.id)

        # ------ TEMP CODE ------
        # Manually promote the properties
        tax_lots = TaxLotState.objects.filter(jurisdiction_tax_lot_id='11160509',
                                              organization=self.org)
        self.assertEqual(len(tax_lots), 1)
        tax_lot_view = tax_lots[0].promote(self.cycle)

        properties = PropertyState.objects.filter(
            pm_property_id__in=['3020139', '4828379', '1154623'])
        property_views = [p.promote(self.cycle) for p in properties]
        self.assertEqual(len(property_views), 3)
        self.assertTrue(isinstance(property_views[0], PropertyView))

        # Check the count of the canonical buildings
        from django.db.models.query import QuerySet
        ps = tasks.list_canonical_property_states(self.org)
        self.assertTrue(isinstance(ps, QuerySet))
        self.assertEqual(len(ps), 3)

        # Manually pair up the ts and ps until the match/pair properties works
        for pv in property_views:
            TaxLotProperty.objects.create(cycle=self.cycle, property_view=pv,
                                          taxlot_view=tax_lot_view)

        # ------ END TEMP CODE ------

        # make sure the the property only has one tax lot and vice versa
        tlv = TaxLotView.objects.filter(state__jurisdiction_tax_lot_id='11160509', cycle=self.cycle)
        self.assertEqual(len(tlv), 1)
        tlv = tlv[0]
        properties = tlv.property_states()
        self.assertEqual(len(properties), 3)
