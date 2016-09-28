# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import datetime
import logging

from seed.data_importer import tasks
from seed.data_importer.tests.util import (
    DataMappingBaseTestCase,
    FAKE_EXTRA_DATA,
    FAKE_MAPPINGS,
    FAKE_ROW,
)
from seed.models import (
    ASSESSED_RAW,
)
from seed.models import (
    Column,
    PropertyState,
    PropertyView,
    DATA_STATE_MAPPING,
    TaxLotState,
    TaxLotProperty,
)
from seed.utils.generic import pp

logger = logging.getLogger(__name__)


class TestCaseA(DataMappingBaseTestCase):

    def setUp(self):
        filename = getattr(self, 'filename', 'example-data-properties.xlsx')
        import_file_source_type = ASSESSED_RAW
        self.fake_mappings = FAKE_MAPPINGS['portfolio']
        self.fake_extra_data = FAKE_EXTRA_DATA
        self.fake_row = FAKE_ROW
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        self.import_file = self.load_import_file_file(filename, self.import_file)

    def test_import_file(self):
        tasks._save_raw_data(self.import_file.pk, 'fake_cache_key', 1)
        Column.create_mappings(self.fake_mappings, self.org, self.user)
        tasks.map_data(self.import_file.pk)

        ps = PropertyState.objects.filter(pm_property_id='2264').first()
        ps.promote(self.cycle)

        ps = self.import_file.find_unmatched_property_states()
        self.assertEqual(len(ps), 11)

    def test_match_buildings(self):
        """Good case for testing our matching system."""
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
        self.assertEqual(len(ts), 12)

        # Check a single case of the taxlotstate
        ts = TaxLotState.objects.filter(jurisdiction_tax_lot_id='1552813').first()
        self.assertEqual(ts.jurisdiction_tax_lot_id, '1552813')
        self.assertEqual(ts.address_line_1, None)
        self.assertEqual(ts.extra_data["extra_data_2"], 1)

        # Check a single case of the propertystate
        ps = PropertyState.objects.filter(pm_property_id='2264')
        self.assertEqual(len(ps), 1)
        ps = ps.first()
        self.assertEqual(ps.pm_property_id, '2264')
        self.assertEqual(ps.address_line_1, '50 Willow Ave SE')
        self.assertEqual(ps.extra_data["extra_data_1"], 'a')
        self.assertEqual('extra_data_2' in ps.extra_data.keys(), False)

        # Promote case A (one property <-> one tax lot) for testing
        # Typically this method should not be called here, rather in the matching code.
        pv = ps.promote(self.cycle)
        tlv = ts.promote(self.cycle)

        # Now try to match the properties and tax lots
        from django.db.models.query import QuerySet
        ps = tasks.list_canonical_property_states(self.org)
        self.assertTrue(isinstance(ps, QuerySet))
        self.assertEqual(len(ps), 1)

        # tasks.match_buildings(self.import_file.id, self.user.id)
        # tasks.pair_buildings(self.import_file.id, self.user.id)

        # Manually pair up the ts and ps until the match/pair properties works
        tlp = TaxLotProperty.objects.create(cycle=self.cycle, property_view=pv, taxlot_view=tlv)

        # make sure the the property only has one tax lot and vice versa
        # ps = PropertyState.objects.filter(pm_property_id='2264').first()

        pv = PropertyView.objects.filter(state__pm_property_id='2264', cycle=self.cycle).first()

        self.assertEqual(len(pv.tax_lots()), 1)

        for tl in pv.tax_lots():
            pp(tl)
