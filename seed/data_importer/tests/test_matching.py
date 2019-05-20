# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from seed.data_importer.tasks import (
    match_buildings,
)
from seed.data_importer.match import (
    filter_duplicate_states,
    save_state_match,
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
    TaxLotState,
    TaxLotView,
)
from seed.test_helpers.fake import (
    # FakePropertyFactory,
    FakePropertyStateFactory,
    FakeTaxLotStateFactory,
    # FakeTaxLotViewFactory,
    # FakePropertyViewFactory,
)
from seed.tests.util import DataMappingBaseTestCase


class TestMatchingInImportFile(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

    def test_duplicate_properties_identified(self):
        base_details = {
            'address_line_1': '123 Match Street',
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create pair of properties that are exact duplicates
        self.property_state_factory.get_property_state(**base_details)
        self.property_state_factory.get_property_state(**base_details)

        # Create a non-matching, non-duplicate property
        base_details['address_line_1'] = '123 Different Ave'
        base_details['city'] = 'Denver'
        self.property_state_factory.get_property_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file.mapping_done = True
        self.import_file.save()
        match_buildings(self.import_file.id)

        # 2 Property, 2 PropertyViews, 3 PropertyState (1 flagged to be ignored)
        self.assertEqual(Property.objects.count(), 2)
        self.assertEqual(PropertyView.objects.count(), 2)
        self.assertEqual(PropertyState.objects.count(), 3)
        self.assertEqual(PropertyState.objects.filter(data_state=DATA_STATE_DELETE).count(), 1)

    def test_duplicate_taxlots_identified(self):
        base_details = {
            'address_line_1': '123 Match Street',
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create pair of properties that are exact duplicates
        self.taxlot_state_factory.get_taxlot_state(**base_details)
        self.taxlot_state_factory.get_taxlot_state(**base_details)

        # Create a non-matching, non-duplicate property
        base_details['address_line_1'] = '123 Different Ave'
        base_details['city'] = 'Denver'
        self.taxlot_state_factory.get_taxlot_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file.mapping_done = True
        self.import_file.save()
        match_buildings(self.import_file.id)

        # 2 TaxLot, 2 TaxLotViews, 3 TaxLotState (1 flagged to be ignored)
        self.assertEqual(TaxLot.objects.count(), 2)
        self.assertEqual(TaxLotView.objects.count(), 2)
        self.assertEqual(TaxLotState.objects.count(), 3)
        self.assertEqual(TaxLotState.objects.filter(data_state=DATA_STATE_DELETE).count(), 1)

    def test_match_properties_if_all_default_fields_match(self):
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

    def test_match_taxlots_if_all_default_fields_match(self):
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

    def test_match_properties_on_ubid(self):
        base_details = {
            'ubid': '86HJPCWQ+2VV-1-3-2-3',
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create set of properties that match each other
        self.property_state_factory.get_property_state(**base_details)
        base_details['city'] = 'Denver'
        self.property_state_factory.get_property_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file.mapping_done = True
        self.import_file.save()
        match_buildings(self.import_file.id)

        # 1 Property, 1 PropertyView, 3 PropertyStates (2 imported, 1 merge result)
        self.assertEqual(Property.objects.count(), 1)
        self.assertEqual(PropertyView.objects.count(), 1)
        self.assertEqual(PropertyState.objects.count(), 3)

    def test_match_properties_normalized_address_used_instead_of_address_line_1(self):
        base_details = {
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create set of properties that have the same address_line_1 in slightly different format
        base_details['address_line_1'] = '123 Match Street'
        self.property_state_factory.get_property_state(**base_details)
        base_details['address_line_1'] = '123 match St.'
        base_details['city'] = 'Denver'
        self.property_state_factory.get_property_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file.mapping_done = True
        self.import_file.save()
        match_buildings(self.import_file.id)

        # 1 Property, 1 PropertyView, 3 PropertyStates (2 imported, 1 merge result)
        self.assertEqual(Property.objects.count(), 1)
        self.assertEqual(PropertyView.objects.count(), 1)
        self.assertEqual(PropertyState.objects.count(), 3)

    def test_match_taxlots_normalized_address_used_instead_of_address_line_1(self):
        base_details = {
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create set of taxlots that have the same address_line_1 in slightly different format
        base_details['address_line_1'] = '123 Match Street'
        self.taxlot_state_factory.get_taxlot_state(**base_details)
        base_details['address_line_1'] = '123 match St.'
        base_details['city'] = 'Denver'
        self.taxlot_state_factory.get_taxlot_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file.mapping_done = True
        self.import_file.save()
        match_buildings(self.import_file.id)

        # 1 TaxLot, 1 TaxLotView, 3 TaxLotStates (2 imported, 1 merge result)
        self.assertEqual(TaxLot.objects.count(), 1)
        self.assertEqual(TaxLotView.objects.count(), 1)
        self.assertEqual(TaxLotState.objects.count(), 3)

    def test_no_matches_if_all_matching_criteria_is_None(self):
        """
        Default matching criteria for PropertyStates are:
            - address_line_1 (substituted by normalized_address)
            - ubid
            - pm_property_id
            - custom_id_1
        and all are set to None.
        """
        base_details = {
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }

        # Create set of properties that won't match
        self.property_state_factory.get_property_state(**base_details)
        base_details['city'] = 'Denver'
        self.property_state_factory.get_property_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file.mapping_done = True
        self.import_file.save()
        match_buildings(self.import_file.id)

        # 2 Property, 2 PropertyView, 2 PropertyStates - No merges
        self.assertEqual(Property.objects.count(), 2)
        self.assertEqual(PropertyView.objects.count(), 2)
        self.assertEqual(PropertyState.objects.count(), 2)

    def test_match_properties_using_extra_data_field(self):
        # Create extra_data column and make it matching criteria
        Column.objects.create(
            organization_id=self.org.id,
            column_name='ed_1',
            is_extra_data=True,
            table_name='PropertyState',
            is_matching_criteria=True
        )

        base_details = {
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
            'extra_data': {'ed_1': 'some matching value'},
        }

        # Create set of properties that have the same extra_data ed_1 value
        self.property_state_factory.get_property_state(**base_details)
        base_details['city'] = 'Denver'
        self.property_state_factory.get_property_state(**base_details)

        # Create a property that has a different extra_data ed_1 value
        base_details['extra_data']['ed_1'] = 'non-matching value'
        self.property_state_factory.get_property_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file.mapping_done = True
        self.import_file.save()
        match_buildings(self.import_file.id)

        # 2 Property, 2 PropertyView, 4 PropertyStates (3 imported, 1 merge result)
        self.assertEqual(Property.objects.count(), 2)
        self.assertEqual(PropertyView.objects.count(), 2)
        self.assertEqual(PropertyState.objects.count(), 4)

    def test_match_taxlots_using_extra_data_field(self):
        # Create extra_data column and make it matching criteria
        Column.objects.create(
            organization_id=self.org.id,
            column_name='ed_1',
            is_extra_data=True,
            table_name='TaxLotState',
            is_matching_criteria=True
        )

        base_details = {
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
            'extra_data': {'ed_1': 'some matching value'},
        }

        # Create set of taxlots that should match
        self.taxlot_state_factory.get_taxlot_state(**base_details)
        base_details['city'] = 'Denver'
        self.taxlot_state_factory.get_taxlot_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file.mapping_done = True
        self.import_file.save()
        match_buildings(self.import_file.id)

        # 1 TaxLot, 1 TaxLotView, 3 TaxLotStates (2 imported, 1 merge result)
        self.assertEqual(TaxLot.objects.count(), 1)
        self.assertEqual(TaxLotView.objects.count(), 1)
        self.assertEqual(TaxLotState.objects.count(), 3)

    def test_match_properties_get_rolled_up_into_one_in_the_order_their_uploaded(self):
        """
        The most recently uploaded should take precedence when merging states.
        If more than 2 states match each other, they are merged two at a time
        until one is remaining.
        """
        base_details = {
            'address_line_1': '123 Match Street',
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create first set of properties that match each other
        base_details['city'] = 'Philadelphia'
        self.property_state_factory.get_property_state(**base_details)
        base_details['city'] = 'Arvada'
        self.property_state_factory.get_property_state(**base_details)
        base_details['city'] = 'Golden'
        self.property_state_factory.get_property_state(**base_details)
        base_details['city'] = 'Denver'
        self.property_state_factory.get_property_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file.mapping_done = True
        self.import_file.save()
        match_buildings(self.import_file.id)

        # 1 Property, 1 PropertyViews, 7 PropertyStates (4 imported, 3 merge results)
        self.assertEqual(Property.objects.count(), 1)
        self.assertEqual(PropertyView.objects.count(), 1)
        self.assertEqual(PropertyState.objects.count(), 7)

        self.assertEqual(PropertyView.objects.first().state.city, 'Denver')


class TestMatchingOutsideImportFile(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file_1, self.import_record_1, self.cycle = selfvars

        self.import_record_2, self.import_file_2 = self.create_import_file(
            self.user, self.org, self.cycle
        )

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

    def test_duplicate_properties_identified(self):
        base_details = {
            'address_line_1': '123 Match Street',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create property in first ImportFile
        ps_1 = self.property_state_factory.get_property_state(**base_details)

        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Create duplicate property coming from second ImportFile
        base_details['import_file_id'] = self.import_file_2.id
        ps_2 = self.property_state_factory.get_property_state(**base_details)

        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        match_buildings(self.import_file_2.id)

        # 1 Property, 1 PropertyViews, 2 PropertyStates
        self.assertEqual(Property.objects.count(), 1)
        self.assertEqual(PropertyView.objects.count(), 1)
        self.assertEqual(PropertyState.objects.count(), 2)

        # Be sure the first property is used in the -View and the second is marked for "deletion"
        self.assertEqual(PropertyView.objects.first().state_id, ps_1.id)
        self.assertEqual(PropertyState.objects.get(data_state=DATA_STATE_DELETE).id, ps_2.id)

    def test_match_properties_if_all_default_fields_match(self):
        base_details = {
            'address_line_1': '123 Match Street',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create property in first ImportFile
        ps_1 = self.property_state_factory.get_property_state(**base_details)

        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Create properties from second ImportFile, one matching existing PropertyState
        base_details['import_file_id'] = self.import_file_2.id

        base_details['city'] = 'Denver'
        ps_2 = self.property_state_factory.get_property_state(**base_details)

        base_details['pm_property_id'] = '11111'
        base_details['city'] = 'Philadelphia'
        ps_3 = self.property_state_factory.get_property_state(**base_details)

        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        match_buildings(self.import_file_2.id)

        # 2 Property, 2 PropertyViews, 4 PropertyStates (3 imported, 1 merge result)
        self.assertEqual(Property.objects.count(), 2)
        self.assertEqual(PropertyView.objects.count(), 2)
        self.assertEqual(PropertyState.objects.count(), 4)

        cities_from_views = []
        ps_ids_from_views = []
        for pv in PropertyView.objects.all():
            cities_from_views.append(pv.state.city)
            ps_ids_from_views.append(pv.state_id)

        self.assertIn('Denver', cities_from_views)
        self.assertIn('Philadelphia', cities_from_views)

        self.assertIn(ps_3.id, ps_ids_from_views)
        self.assertNotIn(ps_1.id, ps_ids_from_views)
        self.assertNotIn(ps_2.id, ps_ids_from_views)

    def test_match_taxlots_if_all_default_fields_match(self):
        base_details = {
            'address_line_1': '123 Match Street',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create property in first ImportFile
        tls_1 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Create properties from second ImportFile, one matching existing PropertyState
        base_details['import_file_id'] = self.import_file_2.id

        base_details['city'] = 'Denver'
        tls_2 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        base_details['jurisdiction_tax_lot_id'] = '11111'
        base_details['city'] = 'Philadelphia'
        tls_3 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        match_buildings(self.import_file_2.id)

        # 2 TaxLot, 2 TaxLotViews, 4 TaxLotStates (3 imported, 1 merge result)
        self.assertEqual(TaxLot.objects.count(), 2)
        self.assertEqual(TaxLotView.objects.count(), 2)
        self.assertEqual(TaxLotState.objects.count(), 4)

        cities_from_views = []
        tls_ids_from_views = []
        for tlv in TaxLotView.objects.all():
            cities_from_views.append(tlv.state.city)
            tls_ids_from_views.append(tlv.state_id)

        self.assertIn('Denver', cities_from_views)
        self.assertIn('Philadelphia', cities_from_views)

        self.assertIn(tls_3.id, tls_ids_from_views)
        self.assertNotIn(tls_1.id, tls_ids_from_views)
        self.assertNotIn(tls_2.id, tls_ids_from_views)

    def test_match_properties_using_extra_data_field(self):
        # Create extra_data column and make it matching criteria
        Column.objects.create(
            organization_id=self.org.id,
            column_name='ed_1',
            is_extra_data=True,
            table_name='PropertyState',
            is_matching_criteria=True
        )

        base_details = {
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
            'extra_data': {'ed_1': 'some matching value'},
        }

        ps_1 = self.property_state_factory.get_property_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Create properties from second ImportFile, one matching existing PropertyState
        base_details['import_file_id'] = self.import_file_2.id
        base_details['city'] = 'Denver'
        ps_2 = self.property_state_factory.get_property_state(**base_details)

        base_details['extra_data']['ed_1'] = 'non-matching value'
        ps_3 = self.property_state_factory.get_property_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        match_buildings(self.import_file_2.id)

        # 2 Property, 2 PropertyView, 4 PropertyStates (3 imported, 1 merge result)
        self.assertEqual(Property.objects.count(), 2)
        self.assertEqual(PropertyView.objects.count(), 2)
        self.assertEqual(PropertyState.objects.count(), 4)

        ps_ids_from_views = [pv.state_id for pv in PropertyView.objects.all()]
        self.assertIn(ps_3.id, ps_ids_from_views)
        self.assertNotIn(ps_1.id, ps_ids_from_views)
        self.assertNotIn(ps_2.id, ps_ids_from_views)

    def test_match_taxlots_using_extra_data_field(self):
        # Create extra_data column and make it matching criteria
        Column.objects.create(
            organization_id=self.org.id,
            column_name='ed_1',
            is_extra_data=True,
            table_name='TaxLotState',
            is_matching_criteria=True
        )

        base_details = {
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
            'extra_data': {'ed_1': 'some matching value'},
        }

        tls_1 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Create taxlots from second ImportFile, one matching existing TaxLotState
        base_details['import_file_id'] = self.import_file_2.id
        base_details['city'] = 'Denver'
        tls_2 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        base_details['extra_data']['ed_1'] = 'non-matching value'
        tls_3 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        # set import_file mapping done so that matching can occur.
        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        match_buildings(self.import_file_2.id)

        # 2 TaxLot, 2 TaxLotView, 4 TaxLotStates (3 imported, 1 merge result)
        self.assertEqual(TaxLot.objects.count(), 2)
        self.assertEqual(TaxLotView.objects.count(), 2)
        self.assertEqual(TaxLotState.objects.count(), 4)

        tls_ids_from_views = [tlv.state_id for tlv in TaxLotView.objects.all()]
        self.assertIn(tls_3.id, tls_ids_from_views)
        self.assertNotIn(tls_1.id, tls_ids_from_views)
        self.assertNotIn(tls_2.id, tls_ids_from_views)


class TestMatchingHelperMethods(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

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

    def test_filter_duplicate_states(self):
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
        uniq_state_ids, dup_state_count = filter_duplicate_states(props)

        # There should be 6 uniq states. 5 from the second call, and one of 'The Same Address'
        self.assertEqual(len(uniq_state_ids), 6)
        self.assertEqual(dup_state_count, 9)
