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
    PropertyView,
    Property,
    TaxLotState,
    TaxLot,
    DATA_STATE_MAPPING,
    ASSESSED_RAW,
)

logger = logging.getLogger(__name__)


class TestCaseMultipleDuplicateMatching(DataMappingBaseTestCase):
    def setUp(self):
        filename = getattr(self, 'filename', 'example-data-properties-duplicates.xlsx')
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

    def test_hash(self):
        self.assertEqual(tasks.hash_state_object(PropertyState()),
                         tasks.hash_state_object(PropertyState(organization=self.org)))

        self.assertEqual(tasks.hash_state_object(TaxLotState()),
                         tasks.hash_state_object(TaxLotState(organization=self.org)))

        ps1 = PropertyState(address_line_1='123 fake st', extra_data={"a": "100"})
        ps2 = PropertyState(address_line_1='123 fake st', extra_data={"a": "200"})
        ps3 = PropertyState(extra_data={"a": "200"})
        ps4 = PropertyState(extra_data={"a": "100"})
        ps5 = PropertyState(address_line_1='123 fake st')

        self.assertEqual(len(set(map(tasks.hash_state_object, [ps1, ps2, ps3, ps4, ps5]))), 5)

    def test_import_duplicates(self):
        # Check to make sure all the properties imported
        ps = PropertyState.objects.filter(
            data_state=DATA_STATE_MAPPING,
            organization=self.org,
            import_file=self.import_file,
        )

        self.assertEqual(len(ps), 9)
        self.assertEqual(PropertyState.objects.filter(pm_property_id='2264').count(), 7)

        hashes = map(tasks.hash_state_object, ps)
        self.assertEqual(len(hashes), 9)
        self.assertEqual(len(set(hashes)), 4)

        unique_property_states, _ = tasks.filter_duplicated_states(ps)
        self.assertEqual(len(unique_property_states), 4)

        tasks.match_buildings(self.import_file.id)

        self.assertEqual(Property.objects.count(), 3)
        self.assertEqual(PropertyView.objects.count(), 3)

        self.assertEqual(PropertyView.objects.filter(state__pm_property_id='2264').count(), 1)

        pv = PropertyView.objects.filter(state__pm_property_id='2264').first()
        self.assertEqual(pv.state.pm_property_id, '2264')
        self.assertEqual(pv.state.gross_floor_area, 12555)
        self.assertEqual(pv.state.energy_score, 75)

        self.assertEqual(TaxLot.objects.count(), 0)

        self.assertEqual(self.import_file.find_unmatched_property_states().count(), 2)
        self.assertEqual(self.import_file.find_unmatched_tax_lot_states().count(), 0)
