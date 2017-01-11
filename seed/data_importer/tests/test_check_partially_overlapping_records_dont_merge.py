# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

# In reference to Github issue: 1107
# https://github.com/SEED-platform/seed/issues/1107

# When the addresses match but the IDs do not match we will not accept
# this.


import logging

from seed.data_importer import tasks
from seed.data_importer.tests.util import (
    DataMappingBaseTestCase,
    FAKE_MAPPINGS,
)
from seed.models import (
    Column,
    TaxLotState,
    TaxLot,
    ASSESSED_RAW,
)

logger = logging.getLogger(__name__)


class TestCaseCheckHalfMatchDoesNotMerge(DataMappingBaseTestCase):

    def setUp(self):
        filename = getattr(self, 'filename', 'taxlot-multiple-id-one-address.xlsx')
        import_file_source_type = ASSESSED_RAW
        self.fake_mappings = FAKE_MAPPINGS['taxlot']

        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        self.import_file = self.load_import_file_file(filename, self.import_file)

    def test_importduplicates(self):
        self.assertEqual(TaxLotState.objects.count(), 0)

        tasks._save_raw_data(self.import_file.pk, 'fake_cache_key', 1)
        Column.create_mappings(self.fake_mappings, self.org, self.user)
        tasks.map_data(self.import_file.pk)

        # tasks._save_raw_data(self.import_file_tax_lot.pk, 'fake_cache_key', 1)

        self.assertEqual(TaxLotState.objects.count(), 2)

        # Because we haven't mapped and merged.
        self.assertEqual(TaxLot.objects.count(), 0)

        tasks.match_buildings(self.import_file.pk, self.user.id)

        self.assertNotEqual(TaxLot.objects.count(), 0)
        self.assertEqual(TaxLot.objects.count(), 2)

        return
