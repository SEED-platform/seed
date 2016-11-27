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
    FAKE_EXTRA_DATA,
    FAKE_MAPPINGS,
    FAKE_ROW,
)
from seed.models import (
    Column,
    PropertyState,
    PropertyView,
    Property,
    PropertyAuditLog,
    TaxLotState,
    TaxLot,
    DATA_STATE_MAPPING,
    ASSESSED_RAW,
)

logger = logging.getLogger(__name__)


class TestCaseCheckHalfMatchDoesNotMerge(DataMappingBaseTestCase):

    def setUp(self):
        filename = getattr(self, 'filename', 'PM_File_test_1108.xlsx')
        import_file_source_type = ASSESSED_RAW
        self.fake_mappings = FAKE_MAPPINGS['portfolio']

        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        self.import_file = self.load_import_file_file(filename, self.import_file)

    def test_importduplicates(self):
        self.assertEqual(Property.objects.count(), 0)
        self.assertEqual(PropertyState.objects.count(), 0)

        tasks._save_raw_data(self.import_file.pk, 'fake_cache_key', 1)
        Column.create_mappings(self.fake_mappings, self.org, self.user)
        tasks.map_data(self.import_file.pk)

        tasks.match_buildings(self.import_file.pk, self.user.id)

        self.assertNotEqual(PropertyState.objects.count(), 0)
        self.assertNotEqual(Property.objects.count(), 0)

        self.assertEqual(PropertyState.objects.filter(pm_property_id='1163866').count(), 1)
        ps = PropertyState.objects.filter(pm_property_id='1163866').first()

        self.assertEqual(ps.energy_score, 281989.0)
        self.assertEqual(ps.owner_email, "trusso@akridge.com")

        self.assertEqual(ps.generation_date.month, 9)
        self.assertEqual(ps.generation_date.day, 30)

        self.assertEqual(ps.release_date.month, 11)
        self.assertEqual(ps.release_date.day, 12)

        self.assertEqual(Property.objects.count(), 4)
        self.assertEqual(PropertyView.objects.count(), 4)


        pv = PropertyView.objects.filter(state__pm_property_id="1180478").first()
        self.assertTrue(pv is not None)

        self.assertEqual(pv.state.energy_score, 459598)

        self.assertEqual(pv.state.address_line_1, "601 13th Street, NW")
        self.assertEqual(pv.state.city, "Washington")

        self.assertEqual(pv.state.owner_email, "kbrokaw@akridge.com")
        self.assertEqual(pv.state.owner_telephone, "202-638-3003")

        pal = PropertyAuditLog.objects.filter(state=pv.state).first()
        self.assertTrue(pal is not None)

        original_import_states = pal.get_import_states()

        self.assertEqual(len(original_import_states), 3)

        s1, s2, s3 = original_import_states

        self.assertEqual(s1.owner_email, "trusso@akridge.com")
        self.assertEqual(s2.owner_email, "kbrokaw@akridge.com")
        self.assertEqual(s3.owner_email, "")


        self.assertEqual(s1.owner_telephone, '202-638-3000')
        self.assertEqual(s2.owner_telephone, '000-000-0000')
        self.assertEqual(s3.owner_telephone, '202-638-3003')

        return
