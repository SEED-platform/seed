# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

# import datetime
#
# from django.utils import timezone as tz

# from seed.data_importer.equivalence_partitioner import EquivalencePartitioner
from seed.data_importer.tasks import (
    match_buildings,
    save_state_match,
    filter_duplicated_states,
    # match_and_merge_unmatched_objects,
)
from seed.models import (
    ASSESSED_RAW,
    DATA_STATE_DELETE,
    DATA_STATE_MAPPING,
    MERGE_STATE_MERGED,
    Column,
    Property,
    PropertyAuditLog,
    PropertyState,
    PropertyView,
    TaxLot,
    # TaxLotProperty,
    TaxLotState,
    TaxLotView,
)
from seed.test_helpers.fake import (
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakeTaxLotStateFactory,
    FakeTaxLotViewFactory,
    FakePropertyViewFactory,
)
from seed.tests.util import DataMappingBaseTestCase


class TestInCycleMatching(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars

        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org,
                                                             cycle=self.cycle)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)
        self.taxlot_view_factory = FakeTaxLotViewFactory(organization=self.org, cycle=self.cycle)

    def test_duplicate_properties_within_same_file_identified(self):
        base_details = {
            'address_line_1': '123 Match Street',
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create pair of properties that are exact duplicates
        self.property_state_factory.get_property_state(**base_details)
        self.property_state_factory.get_property_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file.mapping_done = True
        self.import_file.save()
        match_buildings(self.import_file.id)

        # 1 Property, 1 PropertyViews, 2 PropertyState (1 flagged to be ignored)
        self.assertEqual(Property.objects.count(), 1)
        self.assertEqual(PropertyView.objects.count(), 1)
        self.assertEqual(PropertyState.objects.count(), 2)
        self.assertEqual(PropertyState.objects.filter(data_state=DATA_STATE_DELETE).count(), 1)

    def test_match_properties_within_same_file_if_all_default_fields_match(self):
        base_details = {
            'address_line_1': '123 Match Street',
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create first set of properties that match each other
        self.property_state_factory.get_property_state(**base_details)
        base_details['city'] = 'Denver'
        self.property_state_factory.get_property_state(**base_details)

        # Create second set of properties that match each other
        base_details['pm_property_id'] = '11111'
        self.property_state_factory.get_property_state(**base_details)
        base_details['city'] = 'Philadelphia'
        self.property_state_factory.get_property_state(**base_details)

        # Create unmatched property
        base_details['pm_property_id'] = '000'
        self.property_state_factory.get_property_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file.mapping_done = True
        self.import_file.save()
        match_buildings(self.import_file.id)

        # 3 Property, 3 PropertyViews, 7 PropertyStates (5 imported, 2 merge results)
        self.assertEqual(Property.objects.count(), 3)
        self.assertEqual(PropertyView.objects.count(), 3)
        self.assertEqual(PropertyState.objects.count(), 7)

    def test_match_taxlots_within_same_file_if_all_default_fields_match(self):
        base_details = {
            'address_line_1': '123 Match Street',
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create first set of taxlots that match each other
        self.taxlot_state_factory.get_taxlot_state(**base_details)
        base_details['city'] = 'Denver'
        self.taxlot_state_factory.get_taxlot_state(**base_details)

        # Create second set of taxlots that match each other
        base_details['jurisdiction_tax_lot_id'] = '11111'
        self.taxlot_state_factory.get_taxlot_state(**base_details)
        base_details['city'] = 'Philadelphia'
        self.taxlot_state_factory.get_taxlot_state(**base_details)

        # Create unmatched taxlot
        base_details['jurisdiction_tax_lot_id'] = '000'
        self.taxlot_state_factory.get_taxlot_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file.mapping_done = True
        self.import_file.save()
        match_buildings(self.import_file.id)

        # 3 TaxLot, 3 TaxLotViews, 7 TaxLotStates (5 imported, 2 merge results)
        self.assertEqual(TaxLot.objects.count(), 3)
        self.assertEqual(TaxLotView.objects.count(), 3)
        self.assertEqual(TaxLotState.objects.count(), 7)

    # Tests to write:
    # def test_match_properties_within_same_file_on_ubid(self):
    # def test_match_taxlots_within_same_file_on_ubid(self):
    # def test_match_properties_within_same_file_normalized_address_used_instead_of_address_line_1(self):
    # def test_match_taxlots_within_same_file_normalized_address_used_instead_of_address_line_1(self):
    # def test_match_properties_within_same_file_using_extra_data_field(self):
    # def test_match_taxlots_within_same_file_using_extra_data_field(self):

    # release_date=datetime.datetime(2010, 1, 1, 1, 1, tzinfo=tz.get_current_timezone()),

    def test_save_state_match(self):
        # create a couple states to merge together
        ps_1 = self.property_state_factory.get_property_state(property_name="this should persist")
        ps_2 = self.property_state_factory.get_property_state(
            extra_data={"extra_1": "this should exist too"})

        priorities = Column.retrieve_priorities(self.org.pk)
        merged_state = save_state_match(ps_1, ps_2, priorities)

        self.assertEqual(merged_state.merge_state, MERGE_STATE_MERGED)
        self.assertEqual(merged_state.property_name, ps_1.property_name)
        self.assertEqual(merged_state.extra_data['extra_1'], "this should exist too")

        # verify that the audit log is correct.
        pal = PropertyAuditLog.objects.get(organization=self.org, state=merged_state)
        self.assertEqual(pal.name, 'System Match')
        self.assertEqual(pal.parent_state1, ps_1)
        self.assertEqual(pal.parent_state2, ps_2)
        self.assertEqual(pal.description, 'Automatic Merge')

    def test_filter_duplicated_states(self):
        for i in range(10):
            self.property_state_factory.get_property_state(
                no_default_data=True,
                address_line_1='123 The Same Address',
                # extra_data={"extra_1": "value_%s" % i},
                import_file_id=self.import_file.id,
                data_state=DATA_STATE_MAPPING,
            )
        for i in range(5):
            self.property_state_factory.get_property_state(
                import_file_id=self.import_file.id,
                data_state=DATA_STATE_MAPPING,
            )

        props = self.import_file.find_unmatched_property_states()
        uniq_states, dup_states = filter_duplicated_states(props)

        # There should be 6 uniq states. 5 from the second call, and one of 'The Same Address'
        self.assertEqual(len(uniq_states), 6)
        self.assertEqual(len(dup_states), 9)
