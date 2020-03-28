# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.contrib.postgres.aggregates.general import ArrayAgg

from django.db.models.aggregates import Count

from seed.data_importer.tasks import match_buildings
from seed.models import (
    ASSESSED_RAW,
    DATA_STATE_MAPPING,
    PropertyState,
    PropertyView,
    TaxLotState,
    TaxLotView,
)
from seed.test_helpers.fake import (
    FakePropertyStateFactory,
    FakeTaxLotStateFactory,
    FakeCycleFactory,
)
from seed.tests.util import DataMappingBaseTestCase


class TestMatchMergeLink(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file_1, self.import_record_1, self.cycle_1 = selfvars

        cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.cycle_2 = cycle_factory.get_cycle(name="Cycle 2")
        self.import_record_2, self.import_file_2 = self.create_import_file(
            self.user, self.org, self.cycle_2
        )

        self.cycle_3 = cycle_factory.get_cycle(name="Cycle 3")
        self.import_record_3, self.import_file_3 = self.create_import_file(
            self.user, self.org, self.cycle_3
        )

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

    def test_match_merge_link_for_properties(self):
        """
        In this context, a "set" includes a -State, -View, and canonical record.

        Set up consists of 3 imports across 3 cycles respectively:
        Cycle 1 - 3 sets will be imported.
            - 2 sets match each other and are merged
            - 1 set doesn't match any others
        Cycle 2 - 4 sets will be imported.
            - 3 sets match. All will merge then link to match set in Cycle 1
            - 1 set doesn't match any others
        Cycle 3 - 2 sets will be imported.
            - 1 set will match sets from Cycles 1 and 2 and link to them
            - 1 set doesn't match any others
        """
        # Cycle 1 / ImportFile 1
        base_state_details = {
            'pm_property_id': '1st Match Set',
            'city': '1st Match - Cycle 1 - City 1',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        self.property_state_factory.get_property_state(**base_state_details)

        base_state_details['pm_property_id'] = '1st Match Set'
        base_state_details['city'] = '1st Match - Cycle 1 - City 2'
        self.property_state_factory.get_property_state(**base_state_details)

        base_state_details['pm_property_id'] = 'Single Unmatched - 1'
        base_state_details['city'] = 'Unmatched City - Cycle 1'
        self.property_state_factory.get_property_state(**base_state_details)

        # Import file and create -Views and canonical records.
        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Cycle 2 / ImportFile 2
        base_state_details['import_file_id'] = self.import_file_2.id
        base_state_details['pm_property_id'] = '1st Match Set'
        base_state_details['city'] = '1st Match - Cycle 2 - City 1'
        self.property_state_factory.get_property_state(**base_state_details)

        base_state_details['pm_property_id'] = '1st Match Set'
        base_state_details['city'] = '1st Match - Cycle 2 - City 2'
        self.property_state_factory.get_property_state(**base_state_details)

        base_state_details['pm_property_id'] = '1st Match Set'
        base_state_details['city'] = '1st Match - Cycle 2 - City 3'
        self.property_state_factory.get_property_state(**base_state_details)

        base_state_details['pm_property_id'] = 'Single Unmatched - 2'
        base_state_details['city'] = 'Unmatched City - Cycle 2'
        self.property_state_factory.get_property_state(**base_state_details)

        # Import file and create -Views and canonical records.
        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        match_buildings(self.import_file_2.id)

        # Cycle 3 / ImportFile 3
        base_state_details['import_file_id'] = self.import_file_3.id
        base_state_details['pm_property_id'] = '1st Match Set'
        base_state_details['city'] = '1st Match - Cycle 3 - City 1'
        self.property_state_factory.get_property_state(**base_state_details)

        base_state_details['pm_property_id'] = 'Single Unmatched - 3'
        base_state_details['city'] = 'Unmatched City - Cycle 3'
        self.property_state_factory.get_property_state(**base_state_details)

        # Import file and create -Views and canonical records.
        self.import_file_3.mapping_done = True
        self.import_file_3.save()
        match_buildings(self.import_file_3.id)

        # Verify merges and links happened
        self.assertEqual(6, PropertyView.objects.count())
        self.assertEqual(4 + 6 + 2, PropertyState.objects.count())
        # 4 unique canonical records used in -Views
        # For now, Properties are not deleted when they aren't used in -Views so a count test wouldn't be appropriate
        self.assertEqual(
            4,
            len(set(PropertyView.objects.values_list('property_id', flat=True)))
        )

        # At the moment, there should be 3 -Views with the same canonical record across 3 cycles
        views_with_same_canonical_record = PropertyView.objects.\
            values('property_id').\
            annotate(times_used=Count('id'), cycle_ids=ArrayAgg('cycle_id')).\
            filter(times_used__gt=1).\
            get()
        self.assertEqual(3, views_with_same_canonical_record['times_used'])
        self.assertCountEqual(
            [self.cycle_1.id, self.cycle_2.id, self.cycle_3.id],
            views_with_same_canonical_record['cycle_ids']
        )

    def test_match_merge_link_for_taxlots(self):
        """
        In this context, a "set" includes a -State, -View, and canonical record.

        Set up consists of 3 imports across 3 cycles respectively:
        Cycle 1 - 3 sets will be imported.
            - 2 sets match each other and are merged
            - 1 set doesn't match any others
        Cycle 2 - 4 sets will be imported.
            - 3 sets match. All will merge then link to match set in Cycle 1
            - 1 set doesn't match any others
        Cycle 3 - 2 sets will be imported.
            - 1 set will match sets from Cycles 1 and 2 and link to them
            - 1 set doesn't match any others
        """
        # Cycle 1 / ImportFile 1
        base_state_details = {
            'jurisdiction_tax_lot_id': '1st Match Set',
            'city': '1st Match - Cycle 1 - City 1',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        base_state_details['jurisdiction_tax_lot_id'] = '1st Match Set'
        base_state_details['city'] = '1st Match - Cycle 1 - City 2'
        self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        base_state_details['jurisdiction_tax_lot_id'] = 'Single Unmatched - 1'
        base_state_details['city'] = 'Unmatched City - Cycle 1'
        self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        # Import file and create -Views and canonical records.
        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Cycle 2 / ImportFile 2
        base_state_details['import_file_id'] = self.import_file_2.id
        base_state_details['jurisdiction_tax_lot_id'] = '1st Match Set'
        base_state_details['city'] = '1st Match - Cycle 2 - City 1'
        self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        base_state_details['jurisdiction_tax_lot_id'] = '1st Match Set'
        base_state_details['city'] = '1st Match - Cycle 2 - City 2'
        self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        base_state_details['jurisdiction_tax_lot_id'] = '1st Match Set'
        base_state_details['city'] = '1st Match - Cycle 2 - City 3'
        self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        base_state_details['jurisdiction_tax_lot_id'] = 'Single Unmatched - 2'
        base_state_details['city'] = 'Unmatched City - Cycle 2'
        self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        # Import file and create -Views and canonical records.
        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        match_buildings(self.import_file_2.id)

        # Cycle 3 / ImportFile 3
        base_state_details['import_file_id'] = self.import_file_3.id
        base_state_details['jurisdiction_tax_lot_id'] = '1st Match Set'
        base_state_details['city'] = '1st Match - Cycle 3 - City 1'
        self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        base_state_details['jurisdiction_tax_lot_id'] = 'Single Unmatched - 3'
        base_state_details['city'] = 'Unmatched City - Cycle 3'
        self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        # Import file and create -Views and canonical records.
        self.import_file_3.mapping_done = True
        self.import_file_3.save()
        match_buildings(self.import_file_3.id)

        # Verify merges and links happened
        self.assertEqual(6, TaxLotView.objects.count())
        self.assertEqual(4 + 6 + 2, TaxLotState.objects.count())
        # 4 unique canonical records used in -Views
        # For now, Properties are not deleted when they aren't used in -Views so a count test wouldn't be appropriate
        self.assertEqual(
            4,
            len(set(TaxLotView.objects.values_list('taxlot_id', flat=True)))
        )

        # At the moment, there should be 3 -Views with the same canonical record across 3 cycles
        views_with_same_canonical_record = TaxLotView.objects.\
            values('taxlot_id').\
            annotate(times_used=Count('id'), cycle_ids=ArrayAgg('cycle_id')).\
            filter(times_used__gt=1).\
            get()
        self.assertEqual(3, views_with_same_canonical_record['times_used'])
        self.assertCountEqual(
            [self.cycle_1.id, self.cycle_2.id, self.cycle_3.id],
            views_with_same_canonical_record['cycle_ids']
        )
