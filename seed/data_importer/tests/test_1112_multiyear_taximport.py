# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging
import datetime

from seed.data_importer import tasks
from seed.data_importer.tests.util import (
    DataMappingBaseTestCase,
    FAKE_EXTRA_DATA,
    FAKE_MAPPINGS,
    FAKE_ROW,
)
from seed.models import (
    Cycle,
    Column,
    ImportFile,
    ImportRecord,
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

logger = logging.getLogger(__name__)


class TestCaseMultiYearTest(DataMappingBaseTestCase):

    def setUp(self):
        filename = getattr(self, 'filename', 'example-data-taxlots.xlsx')
        import_file_source_type = ASSESSED_RAW
        self.fake_mappings = FAKE_MAPPINGS['taxlot']
        self.fake_extra_data = FAKE_EXTRA_DATA
        self.fake_row = FAKE_ROW
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file_2015, self.import_record, self.cycle_2015 = selfvars

        self.cycle_2014, _ = Cycle.objects.get_or_create(
            name=u'Test Hack Cycle 2014',
            organization=self.org,
            start=datetime.datetime(2014, 1, 1),
            end=datetime.datetime(2014, 12, 31),
        )

        import_record_2014 = ImportRecord.objects.create(
            owner=self.user, last_modified_by=self.user, super_organization=self.org
        )


        import_file_is_espm = getattr(self, 'import_file_is_espm', True)
        import_file_data_state = getattr(self, 'import_file_data_state', DATA_STATE_IMPORT)

        import_file_2014 = ImportFile.objects.create(import_record=import_record_2014, cycle=self.cycle_2014)
        import_file_2014.is_espm = import_file_is_espm
        import_file_2014.source_type = import_file_source_type
        import_file_2014.data_state = import_file_data_state
        import_file_2014.save()

        self.import_file_2014 = self.load_import_file_file(filename, import_file_2014)
        self.import_file_2015 = self.load_import_file_file(filename, self.import_file_2015)

    def test_multiyear(self):

        tasks._save_raw_data(self.import_file_2014.pk, 'fake_cache_key', 1)
        Column.create_mappings(self.fake_mappings, self.org, self.user)
        tasks.map_data(self.import_file_2014.pk)
        tasks.match_buildings(self.import_file_2014.pk, self.user.id)

        self.assertEqual(TaxLotState.objects.count(), 9)
        self.assertEqual(TaxLotView.objects.count(), 9)
        self.assertEqual(TaxLot.objects.count(), 9)

        self.assertNotEqual(TaxLotView.objects.filter(cycle=self.cycle_2014).count(), 0)
        self.assertEqual(TaxLotView.objects.filter(cycle=self.cycle_2015).count(), 0)

        tasks._save_raw_data(self.import_file_2015.pk, 'fake_cache_key', 1)
        Column.create_mappings(self.fake_mappings, self.org, self.user)
        tasks.map_data(self.import_file_2015.pk)
        tasks.match_buildings(self.import_file_2015.pk, self.user.id)

        self.assertEqual(TaxLot.objects.count(), 9)
        self.assertEqual(TaxLotState.objects.count(), 18)

        self.assertNotEqual(TaxLotView.objects.filter(cycle=self.cycle_2014).count(), 0)
        self.assertNotEqual(TaxLotView.objects.filter(cycle=self.cycle_2015).count(), 0)

        for tl in TaxLot.objects.all():
            self.assertEqual(tl.views.count(), 2)
