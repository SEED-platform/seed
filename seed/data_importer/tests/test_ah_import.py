# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from datetime import datetime

from seed.data_importer.match import match_and_link_incoming_properties_and_taxlots
from seed.lib.progress_data.progress_data import ProgressData
from seed.models import ASSESSED_RAW, DATA_STATE_MAPPING, DATA_STATE_MATCHING, Property, PropertyState, PropertyView
from seed.test_helpers.fake import FakeCycleFactory, FakePropertyFactory, FakePropertyStateFactory, FakePropertyViewFactory
from seed.tests.util import DataMappingBaseTestCase


class TestAHImportFile(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        self.import_file.mapping_done = True
        self.import_file.save()
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)

        # create tree
        self.org.access_level_names = ['1st Gen', '2nd Gen', '3rd Gen']
        mom = self.org.add_new_access_level_instance(self.org.root.id, 'mom')
        self.me_ali = self.org.add_new_access_level_instance(mom.id, 'me')
        self.sister = self.org.add_new_access_level_instance(mom.id, 'sister')
        self.org.save()

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_factory = FakePropertyFactory(organization=self.org)

        self.base_details = {
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
        }

        progress_data = ProgressData(func_name='match_buildings', unique_id=self.import_file)
        sub_progress_data = ProgressData(func_name='match_sub_progress', unique_id=self.import_file)
        self.action_args = [self.import_file.id, progress_data.key, sub_progress_data.key]

        self.blank_result = {
            'import_file_records': None,
            'property_initial_incoming': 0,
            'property_duplicates_against_existing': 0,
            'property_duplicates_within_file': 0,
            'property_duplicates_within_file_errors': 0,
            'property_merges_against_existing': 0,
            'property_merges_against_existing_errors': 0,
            'property_merges_between_existing': 0,
            'property_merges_within_file': 0,
            'property_merges_within_file_errors': 0,
            'property_new': 0,
            'property_new_errors': 0,
            'tax_lot_initial_incoming': 0,
            'tax_lot_duplicates_against_existing': 0,
            'tax_lot_duplicates_within_file': 0,
            'tax_lot_duplicates_within_file_errors': 0,
            'tax_lot_merges_against_existing': 0,
            'tax_lot_merges_against_existing_errors': 0,
            'tax_lot_merges_between_existing': 0,
            'tax_lot_merges_within_file': 0,
            'tax_lot_merges_within_file_errors': 0,
            'tax_lot_new': 0,
            'tax_lot_new_errored': 0,
        }


class TestAHImport(TestAHImportFile):
    def test_hierarchy_set(self):
        # Set Up
        self.base_details['raw_access_level_instance_id'] = self.me_ali.id
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 1
        self.blank_result['property_new'] = 1
        self.assertDictContainsSubset(self.blank_result, results)

        # Assert - Property was created with correct ali
        assert Property.objects.count() == 1
        p = Property.objects.first()
        assert p.access_level_instance == self.me_ali

    def test_no_hierarchy(self):
        # Set Up
        self.base_details['raw_access_level_instance_error'] = 'uh oh'
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 1
        self.blank_result['property_new_errors'] = 1
        for key, value in self.blank_result.items():
            self.assertIn(key, results)
            self.assertEqual(results[key], value)

        # Assert - No property was created
        assert Property.objects.count() == 0
        assert PropertyState.objects.count() == 1


class TestAHImportDuplicateIncoming(TestAHImportFile):
    def setUp(self):
        super().setUp()

        # this causes all the states to be duplicates
        self.base_details['ubid'] = '86HJPCWQ+2VV-1-3-2-3'
        self.base_details['no_default_data'] = False

    def test_duplicate_both_good(self):
        # Set Up
        self.base_details['raw_access_level_instance_id'] = self.me_ali.id
        self.property_state_factory.get_property_state(**self.base_details)

        self.base_details['raw_access_level_instance_id'] = self.me_ali.id
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 2
        self.blank_result['property_duplicates_within_file'] = 1
        self.blank_result['property_new'] = 1
        self.assertDictContainsSubset(self.blank_result, results)

        # Assert - 1 Property, 1 PropertyViews, 2 PropertyStates
        self.assertEqual(Property.objects.count(), 1)
        p = Property.objects.first()
        assert p.access_level_instance == self.me_ali
        assert PropertyState.objects.count() == 2

    def test_duplicate_both_good_but_different_a(self):
        # Set Up
        self.base_details['raw_access_level_instance_id'] = self.org.root.id
        self.property_state_factory.get_property_state(**self.base_details)

        self.base_details['raw_access_level_instance_id'] = self.me_ali.id
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 2
        self.blank_result['property_duplicates_within_file_errors'] = 2
        self.blank_result['property_new'] = 0
        self.assertDictContainsSubset(self.blank_result, results)

        # Assert - No properties created
        self.assertEqual(Property.objects.count(), 0)
        self.assertEqual(PropertyState.objects.count(), 2)

    def test_duplicate_both_good_but_different_b(self):
        # Set Up
        self.base_details['raw_access_level_instance_id'] = self.me_ali.id
        self.property_state_factory.get_property_state(**self.base_details)

        self.base_details['raw_access_level_instance_id'] = self.org.root.id
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 2
        self.blank_result['property_duplicates_within_file_errors'] = 2
        self.blank_result['property_new'] = 0
        self.assertDictContainsSubset(self.blank_result, results)

        # 1 Property, 1 PropertyViews, 2 PropertyStates
        self.assertEqual(Property.objects.count(), 0)
        self.assertEqual(PropertyState.objects.count(), 2)

    def test_duplicate_one_bad_a(self):
        # Set Up
        self.base_details['raw_access_level_instance_error'] = 'uh oh'
        self.property_state_factory.get_property_state(**self.base_details)

        self.base_details['raw_access_level_instance_error'] = None
        self.base_details['raw_access_level_instance_id'] = self.me_ali.id
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 2
        self.blank_result['property_duplicates_within_file'] = 1
        self.blank_result['property_new'] = 1
        self.assertDictContainsSubset(self.blank_result, results)

        # 1 Property, 1 PropertyViews, 2 PropertyStates
        self.assertEqual(Property.objects.count(), 1)
        p = Property.objects.first()
        assert p.access_level_instance == self.me_ali
        assert PropertyState.objects.count() == 2

    def test_duplicate_one_bad_b(self):
        # Set Up
        self.base_details['raw_access_level_instance_id'] = self.me_ali.id
        self.property_state_factory.get_property_state(**self.base_details)

        self.base_details['raw_access_level_instance_error'] = 'uh oh'
        self.base_details['raw_access_level_instance_id'] = None
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 2
        self.blank_result['property_duplicates_within_file'] = 1
        self.blank_result['property_new'] = 1
        self.assertDictContainsSubset(self.blank_result, results)

        # 1 Property, 1 PropertyViews, 2 PropertyStates
        self.assertEqual(Property.objects.count(), 1)
        p = Property.objects.first()
        assert p.access_level_instance == self.me_ali
        assert PropertyState.objects.count() == 2

    def test_duplicate_both_bad(self):
        # Set Up
        self.base_details['raw_access_level_instance_error'] = 'uh oh'
        self.property_state_factory.get_property_state(**self.base_details)

        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 2
        self.blank_result['property_duplicates_within_file'] = 1
        self.blank_result['property_new_errors'] = 1  # cause it doesnt have an ali
        self.assertDictContainsSubset(self.blank_result, results)

        # 0 Property, 0 PropertyViews, 0 PropertyStates
        self.assertEqual(Property.objects.count(), 0)
        self.assertEqual(PropertyState.objects.count(), 2)


class TestAHImportMatchIncoming(TestAHImportFile):
    def setUp(self):
        super().setUp()

        # this causes all the states to match
        self.base_details['ubid'] = '86HJPCWQ+2VV-1-3-2-3'
        self.base_details['no_default_data'] = False

    def test_match_both_good(self):
        # Set Up
        self.base_details['raw_access_level_instance_id'] = self.me_ali.id
        self.property_state_factory.get_property_state(**self.base_details)

        self.base_details['raw_access_level_instance_id'] = self.me_ali.id
        self.base_details['city'] = 'Denver'  # so not duplicate
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 2
        self.blank_result['property_merges_within_file'] = 1
        self.blank_result['property_new'] = 1
        self.assertDictContainsSubset(self.blank_result, results)

        # 1 Property, 1 PropertyView, 3 PropertyStates (2 imported, 1 merge result)
        self.assertEqual(Property.objects.count(), 1)
        p = Property.objects.first()
        assert p.access_level_instance == self.me_ali
        assert PropertyState.objects.count() == 3

    def test_match_both_good_but_different_a(self):
        # Set Up
        self.base_details['raw_access_level_instance_id'] = self.org.root.id
        self.property_state_factory.get_property_state(**self.base_details)

        self.base_details['raw_access_level_instance_id'] = self.me_ali.id
        self.base_details['city'] = 'Denver'  # so not duplicate
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 2
        self.blank_result['property_merges_within_file_errors'] = 2
        self.blank_result['property_new'] = 0
        self.assertDictContainsSubset(self.blank_result, results)

        # No Property and states deleted
        self.assertEqual(Property.objects.count(), 0)
        self.assertEqual(PropertyState.objects.count(), 2)

    def test_match_both_good_but_different_b(self):
        # Set Up
        self.base_details['raw_access_level_instance_id'] = self.me_ali.id
        self.property_state_factory.get_property_state(**self.base_details)

        self.base_details['raw_access_level_instance_id'] = self.org.root.id
        self.base_details['city'] = 'Denver'  # so not duplicate
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 2
        self.blank_result['property_merges_within_file_errors'] = 2
        self.blank_result['property_new'] = 0
        self.assertDictContainsSubset(self.blank_result, results)

        # No Property and states deleted
        self.assertEqual(Property.objects.count(), 0)
        self.assertEqual(PropertyState.objects.count(), 2)

    def test_match_one_bad_a(self):
        # Set Up
        self.base_details['raw_access_level_instance_error'] = 'uh oh'
        self.property_state_factory.get_property_state(**self.base_details)

        self.base_details['raw_access_level_instance_error'] = None
        self.base_details['raw_access_level_instance_id'] = self.org.root.id
        self.base_details['city'] = 'Denver'  # so not duplicate
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 2
        self.blank_result['property_merges_within_file'] = 1
        self.blank_result['property_new'] = 1
        self.assertDictContainsSubset(self.blank_result, results)

        # 1 Property, 1 PropertyView, 3 PropertyStates (2 imported, 1 merge result)
        self.assertEqual(Property.objects.count(), 1)
        p = Property.objects.first()
        assert p.access_level_instance == self.org.root
        assert PropertyState.objects.count() == 3

    def test_match_one_bad_b(self):
        # Set Up
        self.base_details['raw_access_level_instance_id'] = self.me_ali.id
        self.property_state_factory.get_property_state(**self.base_details)

        self.base_details['raw_access_level_instance_error'] = 'uh oh'
        self.base_details['raw_access_level_instance_id'] = None
        self.base_details['city'] = 'Denver'  # so not duplicate
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 2
        self.blank_result['property_merges_within_file'] = 1
        self.blank_result['property_new'] = 1
        self.assertDictContainsSubset(self.blank_result, results)

        # 1 Property, 1 PropertyView, 3 PropertyStates (2 imported, 1 merge result)
        self.assertEqual(Property.objects.count(), 1)
        p = Property.objects.first()
        assert p.access_level_instance == self.me_ali
        assert PropertyState.objects.count() == 3

    def test_match_both_bad(self):
        # Set Up
        self.base_details['raw_access_level_instance_error'] = 'uh oh'
        self.property_state_factory.get_property_state(**self.base_details)

        self.base_details['city'] = 'Denver'  # so not duplicate
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 2
        self.blank_result['property_merges_within_file'] = 1
        self.blank_result['property_new_errors'] = 1
        self.assertDictContainsSubset(self.blank_result, results)

        # No Property created and both states deleted
        self.assertEqual(Property.objects.count(), 0)
        self.assertEqual(PropertyState.objects.count(), 3)


class TestAHImportDuplicateExisting(TestAHImportFile):
    def setUp(self):
        super().setUp()

        # this causes all the states to be duplicates
        self.base_details['no_default_data'] = False

        self.state = self.property_state_factory.get_property_state(**self.base_details)
        self.state.import_file = None
        self.state.save()
        self.existing_property = self.property_factory.get_property(access_level_instance=self.me_ali)
        self.view = PropertyView.objects.create(property=self.existing_property, cycle=self.cycle, state=self.state)

    def test_duplicate_both_good(self):
        # Set Up
        self.base_details['raw_access_level_instance_id'] = self.me_ali.id
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 1
        self.blank_result['property_duplicates_against_existing'] = 1
        self.blank_result['property_new'] = 0
        self.assertDictContainsSubset(self.blank_result, results)

        # 1 Property, 1 PropertyViews, 2 PropertyStates
        self.assertEqual(Property.objects.count(), 1)
        p = Property.objects.first()
        assert p.access_level_instance == self.me_ali
        assert PropertyState.objects.count() == 2

    def test_duplicate_both_good_but_different(self):
        # Set Up
        self.base_details['raw_access_level_instance_id'] = self.org.root.id
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 1
        self.blank_result['property_duplicates_against_existing'] = 1
        self.blank_result['property_new'] = 0
        self.assertDictContainsSubset(self.blank_result, results)

        # No Property and states deleted
        self.assertEqual(Property.objects.count(), 1)
        self.assertEqual(PropertyState.objects.count(), 2)

    def test_duplicate_both_good_but_no_access_to_existing(self):
        # Set Up
        self.existing_property.access_level_instance = self.sister
        self.existing_property.save()
        self.import_record.access_level_instance = self.me_ali
        self.import_record.save()

        self.base_details['raw_access_level_instance_id'] = self.me_ali.id
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 1
        self.blank_result['property_duplicates_against_existing'] = 1
        self.blank_result['property_new'] = 0
        self.assertDictContainsSubset(self.blank_result, results)

        # Only one Property
        self.assertEqual(Property.objects.count(), 1)

        # unmerged
        self.assertEqual(PropertyState.objects.count(), 2)

        # city unchanged
        assert PropertyView.objects.count() == 1
        pv = PropertyView.objects.first()
        assert pv.state.city is None

    def test_duplicate_incoming_error(self):
        # Set Up
        self.base_details['raw_access_level_instance_error'] = 'uh oh'
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 1
        self.blank_result['property_duplicates_against_existing'] = 1
        self.blank_result['property_new'] = 0
        self.assertDictContainsSubset(self.blank_result, results)

        # 1 Property, 1 PropertyViews, 2 PropertyStates
        self.assertEqual(Property.objects.count(), 1)
        p = Property.objects.first()
        assert p.access_level_instance == self.me_ali
        assert PropertyState.objects.count() == 2

    def test_duplicate_incoming_error_and_no_access_to_existing(self):
        # Set Up
        self.existing_property.access_level_instance = self.sister
        self.existing_property.save()
        self.import_record.access_level_instance = self.me_ali
        self.import_record.save()

        self.base_details['raw_access_level_instance_id'] = None
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 1
        self.blank_result['property_duplicates_against_existing'] = 1
        self.blank_result['property_new'] = 0
        self.assertDictContainsSubset(self.blank_result, results)

        # Only one Property
        self.assertEqual(Property.objects.count(), 1)

        # unmerged
        self.assertEqual(PropertyState.objects.count(), 2)

        # city unchanged
        assert PropertyView.objects.count() == 1
        pv = PropertyView.objects.first()
        assert pv.state.city is None


class TestAHImportMatchExisting(TestAHImportFile):
    def setUp(self):
        super().setUp()

        # this causes all the states to match
        self.base_details['ubid'] = '86HJPCWQ+2VV-1-3-2-3'
        self.base_details['no_default_data'] = False

        self.state = self.property_state_factory.get_property_state(**self.base_details)
        self.state.data_state = DATA_STATE_MATCHING
        self.state.save()
        self.existing_property = self.property_factory.get_property(access_level_instance=self.me_ali)
        self.view = PropertyView.objects.create(property=self.existing_property, cycle=self.cycle, state=self.state)

    def test_match_both_good(self):
        # Set Up
        self.base_details['raw_access_level_instance_id'] = self.me_ali.id
        self.base_details['city'] = 'Denver'  # so not duplicate
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 1
        self.blank_result['property_merges_against_existing'] = 1
        self.blank_result['property_new'] = 0
        self.assertDictContainsSubset(self.blank_result, results)

        # one Property in right ali
        self.assertEqual(Property.objects.count(), 1)
        p = Property.objects.first()
        assert p.access_level_instance == self.me_ali

        # merged
        assert PropertyState.objects.count() == 3

        # city changed
        assert PropertyView.objects.count() == 1
        pv = PropertyView.objects.first()
        assert pv.state.city == 'Denver'

    def test_match_both_good_but_different(self):
        # Set Up
        self.base_details['raw_access_level_instance_id'] = self.org.root.id
        self.base_details['city'] = 'Denver'  # so not duplicate
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 1
        self.blank_result['property_merges_against_existing_errors'] = 1
        self.blank_result['property_new'] = 0
        self.assertDictContainsSubset(self.blank_result, results)

        # Only one Property
        self.assertEqual(Property.objects.count(), 1)

        # unmerged
        self.assertEqual(PropertyState.objects.count(), 2)

        # city unchanged
        assert PropertyView.objects.count() == 1
        pv = PropertyView.objects.first()
        assert pv.state.city is None

    def test_match_both_good_but_no_access_to_existing(self):
        # Set Up
        self.existing_property.access_level_instance = self.sister
        self.existing_property.save()
        self.import_record.access_level_instance = self.me_ali
        self.import_record.save()

        self.base_details['raw_access_level_instance_id'] = self.me_ali.id
        self.base_details['city'] = 'Denver'  # so not duplicate
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 1
        self.blank_result['property_merges_against_existing_errors'] = 1
        self.blank_result['property_new'] = 0
        self.assertDictContainsSubset(self.blank_result, results)

        # Only one Property
        self.assertEqual(Property.objects.count(), 1)

        # unmerged
        self.assertEqual(PropertyState.objects.count(), 2)

        # city unchanged
        assert PropertyView.objects.count() == 1
        pv = PropertyView.objects.first()
        assert pv.state.city is None

    def test_match_incoming_error(self):
        # Set Up
        self.base_details['raw_access_level_instance_error'] = 'uh oh'
        self.base_details['city'] = 'Denver'  # so not duplicate
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 1
        self.blank_result['property_merges_against_existing'] = 1
        self.blank_result['property_new'] = 0
        self.assertDictContainsSubset(self.blank_result, results)

        # Only one Property
        self.assertEqual(Property.objects.count(), 1)

        # city unchanged
        assert PropertyView.objects.count() == 1
        pv = PropertyView.objects.first()
        assert pv.state.city == 'Denver'

        # merged
        self.assertEqual(PropertyState.objects.count(), 3)

    def test_match_incoming_error_and_no_access_to_existing(self):
        # Set Up
        self.existing_property.access_level_instance = self.sister
        self.existing_property.save()
        self.import_record.access_level_instance = self.me_ali
        self.import_record.save()

        self.base_details['raw_access_level_instance_id'] = None
        self.base_details['city'] = 'Denver'  # so not duplicate
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 1
        self.blank_result['property_merges_against_existing_errors'] = 1
        self.blank_result['property_new'] = 0
        self.assertDictContainsSubset(self.blank_result, results)

        # Only one Property
        self.assertEqual(Property.objects.count(), 1)

        # unmerged
        self.assertEqual(PropertyState.objects.count(), 2)

        # city unchanged
        assert PropertyView.objects.count() == 1
        pv = PropertyView.objects.first()
        assert pv.state.city is None


class TestAHImportMatchExistingDifferentCycle(TestAHImportFile):
    def setUp(self):
        super().setUp()

        self.property_view_factory = FakePropertyViewFactory(organization=self.org)

        # this causes all the states to match
        self.base_details['ubid'] = '86HJPCWQ+2VV-1-3-2-3'
        self.base_details['no_default_data'] = False

        self.state = self.property_state_factory.get_property_state(**self.base_details)
        self.state.data_state = DATA_STATE_MATCHING
        self.state.save()
        self.existing_property = self.property_factory.get_property(access_level_instance=self.me_ali)
        self.other_cycle = self.cycle_factory.get_cycle(start=datetime(2010, 10, 10))
        self.view = PropertyView.objects.create(property=self.existing_property, cycle=self.other_cycle, state=self.state)

    def test_has_ali_merges_and_links(self):
        # Set Up - create view for merge
        self.property_view_factory.get_property_view(prprty=self.existing_property, cycle=self.cycle)

        # Set Up - update new state info
        self.base_details['raw_access_level_instance_id'] = self.me_ali.id
        self.base_details['city'] = 'Denver'  # so not duplicate
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 1
        self.blank_result['property_merges_against_existing'] = 1
        self.blank_result['property_links_against_existing'] = 0  # not 1 cause the view it merged into was already linked
        self.blank_result['property_new'] = 0  # not 1 cause the property already exists
        self.assertDictContainsSubset(self.blank_result, results)

        # one Property in right ali
        self.assertEqual(Property.objects.count(), 1)
        p = Property.objects.first()
        assert p.access_level_instance == self.me_ali

        # 3 in a little merge tree, 1 in the other cycle
        assert PropertyState.objects.count() == 4

        # city changed in the correct view
        assert PropertyView.objects.count() == 2
        view_info = PropertyView.objects.values('property_id', 'cycle_id', 'state__city')
        assert list(view_info) == [
            {
                'property_id': self.existing_property.id,
                'cycle_id': self.other_cycle.id,
                'state__city': None,
            },
            {
                'property_id': self.existing_property.id,
                'cycle_id': self.cycle.id,
                'state__city': 'Denver',
            },
        ]

    def test_no_ali_merges_and_links(self):
        # Set Up - create view for merge
        self.property_view_factory.get_property_view(prprty=self.existing_property, cycle=self.cycle)

        # Set Up - update new state info
        self.base_details['raw_access_level_instance_error'] = 'uh oh'
        self.base_details['city'] = 'Denver'  # so not duplicate
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 1
        self.blank_result['property_merges_against_existing'] = 1
        self.blank_result['property_links_against_existing'] = 0  # not 1 cause the view it merged into was already linked
        self.blank_result['property_new'] = 0  # not 1 cause the property already exists
        self.assertDictContainsSubset(self.blank_result, results)

        # one Property in right ali
        self.assertEqual(Property.objects.count(), 1)
        p = Property.objects.first()
        assert p.access_level_instance == self.me_ali

        # 3 in a little merge tree, 1 in the other cycle
        assert PropertyState.objects.count() == 4

        # city changed in the correct view
        assert PropertyView.objects.count() == 2
        view_info = PropertyView.objects.values('property_id', 'cycle_id', 'state__city')

        assert list(view_info) == [
            {
                'property_id': self.existing_property.id,
                'cycle_id': self.other_cycle.id,
                'state__city': None,
            },
            {
                'property_id': self.existing_property.id,
                'cycle_id': self.cycle.id,
                'state__city': 'Denver',
            },
        ]

    def test_has_ali_links(self):
        # Set Up - update new state info
        self.base_details['raw_access_level_instance_id'] = self.me_ali.id
        self.base_details['city'] = 'Denver'  # so not duplicate
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 1
        self.blank_result['property_links_against_existing'] = 1
        self.blank_result['property_new'] = 0  # not 1 cause the property already exists
        self.assertDictContainsSubset(self.blank_result, results)

        # 1 in each cycle
        assert PropertyState.objects.count() == 2

        # city changed in the correct view
        assert PropertyView.objects.count() == 2
        view_info = PropertyView.objects.values('property_id', 'property__access_level_instance_id', 'cycle_id', 'state__city')
        assert list(view_info) == [
            {
                'property_id': self.existing_property.id,
                'property__access_level_instance_id': self.me_ali.id,
                'cycle_id': self.other_cycle.id,
                'state__city': None,
            },
            {
                'property_id': self.existing_property.id,
                'property__access_level_instance_id': self.me_ali.id,
                'cycle_id': self.cycle.id,
                'state__city': 'Denver',
            },
        ]

    def test_has_ali_links_different_ali(self):
        # Set Up - update existing state ali
        self.existing_property.access_level_instance = self.sister
        self.existing_property.save()

        # Set Up - update new state info
        self.base_details['raw_access_level_instance_id'] = self.me_ali.id  # different ali
        self.base_details['city'] = 'Denver'  # so not duplicate
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 1
        self.blank_result['property_links_against_existing_errors'] = 1
        self.assertDictContainsSubset(self.blank_result, results)

        # theres two Properties and two PropertyStates, but one of each is abandoned
        self.assertEqual(Property.objects.count(), 2)
        assert PropertyState.objects.count() == 2

        # no change
        assert PropertyView.objects.count() == 1
        view_info = PropertyView.objects.values('property_id', 'property__access_level_instance_id', 'cycle_id', 'state__city')
        assert list(view_info) == [
            {
                'property_id': self.existing_property.id,
                'property__access_level_instance_id': self.sister.id,
                'cycle_id': self.other_cycle.id,
                'state__city': None,
            },
        ]

    def test_no_ali_links(self):
        # Set Up - update new state info
        self.base_details['raw_access_level_instance_error'] = 'uh oh'
        self.base_details['city'] = 'Denver'  # so not duplicate
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 1
        self.blank_result['property_links_against_existing'] = 1
        self.blank_result['property_new'] = 0  # not 1 cause the property already exists
        self.assertDictContainsSubset(self.blank_result, results)

        # two properties, but one abandoned
        self.assertEqual(Property.objects.count(), 2)

        # 1 in each cycle
        assert PropertyState.objects.count() == 2

        # city changed in the correct view
        assert PropertyView.objects.count() == 2
        view_info = PropertyView.objects.values('property_id', 'cycle_id', 'state__city')
        assert list(view_info) == [
            {
                'property_id': self.existing_property.id,
                'cycle_id': self.other_cycle.id,
                'state__city': None,
            },
            {
                'property_id': self.existing_property.id,
                'cycle_id': self.cycle.id,
                'state__city': 'Denver',
            },
        ]

    def test_no_ali_links_no_access(self):
        # Set Up - file and existing property have different alis
        self.existing_property.access_level_instance = self.sister
        self.existing_property.save()
        self.import_record.access_level_instance = self.me_ali
        self.import_record.save()

        # update new state info
        self.base_details['raw_access_level_instance_error'] = 'uh oh'
        self.base_details['city'] = 'Denver'  # so not duplicate
        self.property_state_factory.get_property_state(**self.base_details)

        # Action
        results = match_and_link_incoming_properties_and_taxlots(*self.action_args)

        # Assert - results
        self.blank_result['property_initial_incoming'] = 1
        self.blank_result['property_links_against_existing_errors'] = 1
        self.assertDictContainsSubset(self.blank_result, results)

        # one Property in right ali
        self.assertEqual(Property.objects.count(), 1)
        p = Property.objects.first()
        assert p.access_level_instance == self.sister

        # no change
        assert PropertyView.objects.count() == 1
        view_info = PropertyView.objects.values('property_id', 'cycle_id', 'state__city')
        assert list(view_info) == [
            {
                'property_id': self.existing_property.id,
                'cycle_id': self.other_cycle.id,
                'state__city': None,
            },
        ]
