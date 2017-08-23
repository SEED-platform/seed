# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import copy
import os.path as osp

from seed.data_importer import tasks
from seed.data_importer.tests.util import (
    DataMappingBaseTestCase,
    FAKE_MAPPINGS,
)
from seed.models import (
    Column,
    PropertyState,
    ASSESSED_RAW,
    DATA_STATE_MAPPING,
    DATA_STATE_MATCHING,
    MERGE_STATE_UNKNOWN,
    MERGE_STATE_NEW,
)


class TestProperties(DataMappingBaseTestCase):
    def setUp(self):
        # for now just import some test data. I'd rather create fake data... next time.
        filename = getattr(self, 'filename', 'example-data-properties.xlsx')
        self.fake_mappings = copy.copy(FAKE_MAPPINGS['portfolio'])
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        self.import_file.load_import_file(
            osp.join(osp.dirname(__file__), '../data_importer/tests/data', filename))
        tasks._save_raw_data(self.import_file.pk, 'fake_cache_key', 1)
        Column.create_mappings(self.fake_mappings, self.org, self.user, self.import_file.id)
        tasks.map_data(self.import_file.pk)
        tasks.match_buildings(self.import_file.id)

        # import second file that is currently the same, but should be slightly different
        filename_2 = getattr(self, 'filename', 'example-data-properties-small-changes.xlsx')
        _, self.import_file_2 = self.create_import_file(self.user, self.org, self.cycle)
        self.import_file_2.load_import_file(
            osp.join(osp.dirname(__file__), '../data_importer/tests/data', filename_2))
        tasks._save_raw_data(self.import_file_2.pk, 'fake_cache_key_2', 1)
        tasks.map_data(self.import_file_2.pk)
        tasks.match_buildings(self.import_file_2.id)

    def test_coparent(self):
        # find a state id
        # get a specific test case with coparents
        property_state = PropertyState.objects.filter(
            use_description='Pizza House',
            import_file_id=self.import_file_2,
            data_state__in=[DATA_STATE_MAPPING, DATA_STATE_MATCHING],
            merge_state__in=[MERGE_STATE_UNKNOWN, MERGE_STATE_NEW]
        ).first()

        coparent, count = PropertyState.coparent(property_state.id)

        self.assertEqual(count, 1)
        expected = PropertyState.objects.filter(
            use_description='Retail',
            address_line_1=property_state.address_line_1,
            import_file_id=self.import_file,
            data_state__in=[DATA_STATE_MAPPING, DATA_STATE_MATCHING],
            merge_state__in=[MERGE_STATE_UNKNOWN, MERGE_STATE_NEW]
        ).first()

        self.assertEqual(expected.pk, coparent[0]['id'])
