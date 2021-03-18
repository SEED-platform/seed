# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import copy
import os.path as osp

from django.core.files.uploadedfile import SimpleUploadedFile

from seed.data_importer import tasks
from seed.data_importer.tests.util import (
    FAKE_MAPPINGS,
)
from seed.models import (
    Column,
    TaxLotState,
    ASSESSED_RAW,
    DATA_STATE_MATCHING,
    MERGE_STATE_UNKNOWN,
    MERGE_STATE_NEW,
    MERGE_STATE_MERGED,
)
from seed.tests.util import DataMappingBaseTestCase


class TestProperties(DataMappingBaseTestCase):
    def setUp(self):
        # for now just import some test data. I'd rather create fake data... next time.
        filename = getattr(self, 'filename', 'example-data-properties.xlsx')
        self.fake_mappings = copy.copy(FAKE_MAPPINGS['portfolio'])
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        filepath = osp.join(osp.dirname(__file__), '..', 'data', filename)
        self.import_file.file = SimpleUploadedFile(
            name=filename,
            content=open(filepath, 'rb').read()
        )
        self.import_file.save()

        tasks.save_raw_data(self.import_file.pk)
        Column.create_mappings(self.fake_mappings, self.org, self.user, self.import_file.id)
        tasks.map_data(self.import_file.pk)
        tasks.geocode_and_match_buildings_task(self.import_file.id)

        # import second file with tax lot information
        filename_2 = getattr(self, 'filename', 'example-data-taxlots.xlsx')
        self.fake_mappings = copy.copy(FAKE_MAPPINGS['taxlot'])
        _, self.import_file_2 = self.create_import_file(self.user, self.org, self.cycle)
        filepath = osp.join(osp.dirname(__file__), '..', 'data', filename_2)
        self.import_file_2.file = SimpleUploadedFile(
            name=filename_2,
            content=open(filepath, 'rb').read()
        )
        self.import_file_2.save()

        tasks.save_raw_data(self.import_file_2.pk)
        Column.create_mappings(self.fake_mappings, self.org, self.user, self.import_file.id)
        tasks.map_data(self.import_file_2.pk)
        tasks.geocode_and_match_buildings_task(self.import_file_2.id)

        # import third file with updated tax lot information
        # filename_3 = getattr(self, 'filename', 'example-data-taxlots-small-changes.xlsx')
        # self.fake_mappings = copy.copy(FAKE_MAPPINGS['taxlot'])
        # _, self.import_file_3 = self.create_import_file(self.user, self.org, self.cycle)
        # filepath = osp.join(osp.dirname(__file__), '../data_importer/tests/data', filename_3)
        # self.import_file_3.file = SimpleUploadedFile(
        #     name=filename_3,
        #     content=open(filepath, 'rb').read()
        # )
        # self.import_file_3.save()
        #
        # tasks.save_raw_data(self.import_file_3.pk')
        # tasks.map_data(self.import_file_3.pk)
        # tasks.geocode_and_match_buildings_task(self.import_file_3.id)

    def test_coparent(self):
        # get the main taxlot state
        taxlot_state = TaxLotState.objects.filter(
            jurisdiction_tax_lot_id='1552813',
            import_file_id=self.import_file,
            data_state__in=[DATA_STATE_MATCHING],
            merge_state__in=[MERGE_STATE_UNKNOWN, MERGE_STATE_NEW]
        ).first()

        coparent, count = TaxLotState.coparent(taxlot_state.id)
        self.assertEqual(count, 1)

        # coparent shouldn't have any extra data (unlike the parent which has data_008 from the property mapping
        self.assertEqual(taxlot_state.extra_data['data_008'], 1)
        self.assertEqual(taxlot_state.number_properties, None)
        self.assertEqual(coparent[0]['extra_data'], {})
        self.assertEqual(coparent[0]['number_properties'], 12)

    def test_get_history(self):
        # get the taxlot state that was merged to test the history method
        taxlot_state = TaxLotState.objects.filter(
            jurisdiction_tax_lot_id='1552813',
            data_state__in=[DATA_STATE_MATCHING],
            merge_state__in=[MERGE_STATE_MERGED]
        ).first()
        self.assertIsNotNone(taxlot_state)
        history, master = taxlot_state.history()

        self.assertEqual(master['state_id'], taxlot_state.id)

        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['filename'], 'example-data-taxlots.xlsx')
        self.assertEqual(history[1]['filename'], 'example-data-properties.xlsx')
