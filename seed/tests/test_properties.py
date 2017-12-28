# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import copy
import os.path as osp

from django.core.files.uploadedfile import SimpleUploadedFile

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
    MERGE_STATE_MERGED,
)


class TestProperties(DataMappingBaseTestCase):
    def setUp(self):
        # for now just import some test data. I'd rather create fake data... next time.
        filename = getattr(self, 'filename', 'example-data-properties.xlsx')
        self.fake_mappings = copy.copy(FAKE_MAPPINGS['portfolio'])
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        filepath = osp.join(osp.dirname(__file__), '../data_importer/tests/data', filename)
        self.import_file.file = SimpleUploadedFile(
            name=filename,
            content=open(filepath, 'rb').read()
        )
        self.import_file.save()

        tasks._save_raw_data(self.import_file.pk, 'fake_cache_key', 1)
        Column.create_mappings(self.fake_mappings, self.org, self.user, self.import_file.id)
        tasks.map_data(self.import_file.pk)
        tasks.match_buildings(self.import_file.id)

        # import second file that is currently the same, but should be slightly different
        filename_2 = getattr(self, 'filename', 'example-data-properties-small-changes.xlsx')
        _, self.import_file_2 = self.create_import_file(self.user, self.org, self.cycle)
        filepath = osp.join(osp.dirname(__file__), '../data_importer/tests/data', filename_2)
        self.import_file_2.file = SimpleUploadedFile(
            name=filename_2,
            content=open(filepath, 'rb').read()
        )
        self.import_file_2.save()

        tasks._save_raw_data(self.import_file_2.pk, 'fake_cache_key_2', 1)
        tasks.map_data(self.import_file_2.pk)
        tasks.match_buildings(self.import_file_2.id)

    def test_coparent(self):
        # find a state id
        # get a specific test case with coparents.
        #   Pizza House is the Child
        #   Retail is the Master / Parent
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

    def test_get_history(self):
        # This is the last property state
        property_state = PropertyState.objects.filter(
            use_description='Pizza House',
            ubid='M7RZ35FK+6LL-M7RZ35FK+9GS-M7RZ35FK+H0V',
            data_state__in=[DATA_STATE_MAPPING, DATA_STATE_MATCHING],
            merge_state__in=[MERGE_STATE_MERGED]
        ).first()
        self.assertIsNotNone(property_state)
        history, master = property_state.history()

        self.assertEqual(master['state_id'], property_state.id)

        # self.assertEqual(len(history), 2)


        self.assertIsNotNone(history)

