# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging
import os.path as osp

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
    TaxLotState,
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
        self.import_file.load_import_file(osp.join(osp.dirname(__file__), 'data', filename))
        tasks._save_raw_data(self.import_file.pk, 'fake_cache_key', 1)
        Column.create_mappings(self.fake_mappings, self.org, self.user)
        tasks.map_data(self.import_file.pk)

    def test_match_buildings(self):
        """ case B (many property <-> one tax lot) """
        tasks._save_raw_data(self.import_file.pk, 'fake_cache_key', 1)
        Column.create_mappings(self.fake_mappings, self.org, self.user)
        # Set remap to True because for some reason this file id has been imported before.
        tasks.map_data(self.import_file.pk, True)

        # Check to make sure all the properties imported
        ps = PropertyState.objects.filter(
            data_state=DATA_STATE_MAPPING,
            organization=self.org,
            import_file=self.import_file,
        )
        self.assertEqual(len(ps), 14)

        # Check to make sure the tax lots were imported
        ts = TaxLotState.objects.filter(
            data_state=DATA_STATE_MAPPING,
            organization=self.org,
            import_file=self.import_file,
        )
        self.assertEqual(len(ts), 18)

        # verify that the lot_number has the tax_lot information. For this case it is one-to-many
        p_test = PropertyState.objects.filter(
            pm_property_id='5233255',
            organization=self.org,
            data_state=DATA_STATE_MAPPING,
            import_file=self.import_file,
        ).first()
        self.assertEqual(p_test.lot_number, "33366555;33366125;33366148")

        tasks.match_buildings(self.import_file.id)

        # make sure the the property only has one tax lot and vice versa
        tlv = TaxLotView.objects.filter(state__jurisdiction_tax_lot_id='11160509', cycle=self.cycle)
        self.assertEqual(len(tlv), 1)
        tlv = tlv[0]
        properties = tlv.property_states()
        self.assertEqual(len(properties), 3)
