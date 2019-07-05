# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import json

from django.core.urlresolvers import reverse

from seed.data_importer.tasks import match_buildings

from seed.models import (
    ASSESSED_RAW,
    DATA_STATE_MAPPING,
    Property,
    PropertyAuditLog,
    PropertyState,
    PropertyView,
    TaxLot,
    TaxLotAuditLog,
    TaxLotState,
    TaxLotView,
)
from seed.utils.match import match_merge_in_cycle
from seed.test_helpers.fake import (
    FakePropertyStateFactory,
    FakeTaxLotStateFactory,
)
from seed.tests.util import DataMappingBaseTestCase


class TestMatchingPostEdit(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars

        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.client.login(**user_details)

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

    def test_match_merge_happens_after_property_edit(self):
        base_details = {
            'pm_property_id': '789DifferentID',
            'city': 'Golden',
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create 3 non-matching properties
        ps_1 = self.property_state_factory.get_property_state(**base_details)

        base_details['pm_property_id'] = '123MatchID'
        base_details['city'] = 'Denver'
        self.property_state_factory.get_property_state(**base_details)

        base_details['pm_property_id'] = '1337AnotherDifferentID'
        base_details['city'] = 'Philadelphia'
        ps_3 = self.property_state_factory.get_property_state(**base_details)

        self.import_file.mapping_done = True
        self.import_file.save()
        match_buildings(self.import_file.id)

        # Edit the first property to match the second
        new_data = {
            "state": {
                "pm_property_id": "123MatchID"
            }
        }
        target_view_id = ps_1.propertyview_set.first().id
        url = reverse('api:v2:properties-detail', args=[target_view_id]) + '?organization_id={}'.format(self.org.pk)
        raw_response = self.client.put(url, json.dumps(new_data), content_type='application/json')
        response = json.loads(raw_response.content)

        self.assertEqual(response['match_merged_count'], 2)

        changed_view = PropertyView.objects.exclude(state_id=ps_3).get()
        self.assertEqual(response['view_id'], changed_view.id)

        # Verify that properties 1 and 2 have been merged
        self.assertEqual(Property.objects.count(), 2)
        self.assertEqual(PropertyState.objects.count(), 5)  # Original 3 + 1 edit + 1 merge result
        self.assertEqual(PropertyView.objects.count(), 2)

        # It will have a -State having city as Golden
        self.assertEqual(changed_view.state.city, 'Golden')

        # The corresponding log should be a System Match
        audit_log = PropertyAuditLog.objects.get(state_id=changed_view.state_id)
        self.assertEqual(audit_log.name, 'System Match')

        # Update the edit and match-merge result -State
        new_data = {
            "state": {
                "pm_property_id": "1337AnotherDifferentID"
            }
        }
        url = reverse('api:v2:properties-detail', args=[changed_view.id]) + '?organization_id={}'.format(self.org.pk)
        raw_response = self.client.put(url, json.dumps(new_data), content_type='application/json')
        response = json.loads(raw_response.content)

        # Verify that there's only 1 canonical Property and View left
        self.assertEqual(Property.objects.count(), 1)
        # 6 -States since, 5 from 1st round + 1 from merge
        # None created during edit since the audit log isn't named 'Import Creation'
        self.assertEqual(PropertyState.objects.count(), 6)
        self.assertEqual(PropertyView.objects.count(), 1)
        view = PropertyView.objects.first()

        self.assertEqual(response['view_id'], view.id)

        # Check that city is still Golden, since the edited -State takes precedence
        self.assertEqual(view.state.city, 'Golden')

    def test_match_merge_happens_after_taxlot_edit(self):
        base_details = {
            'jurisdiction_tax_lot_id': '789DifferentID',
            'city': 'Golden',
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create 3 non-matching taxlots
        tls_1 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        base_details['jurisdiction_tax_lot_id'] = '123MatchID'
        base_details['city'] = 'Denver'
        self.taxlot_state_factory.get_taxlot_state(**base_details)

        base_details['jurisdiction_tax_lot_id'] = '1337AnotherDifferentID'
        base_details['city'] = 'Philadelphia'
        tls_3 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        self.import_file.mapping_done = True
        self.import_file.save()
        match_buildings(self.import_file.id)

        # Edit the first taxlot to match the second
        new_data = {
            "state": {
                "jurisdiction_tax_lot_id": "123MatchID"
            }
        }
        target_view_id = tls_1.taxlotview_set.first().id
        url = reverse('api:v2:taxlots-detail', args=[target_view_id]) + '?organization_id={}'.format(self.org.pk)
        raw_response = self.client.put(url, json.dumps(new_data), content_type='application/json')
        response = json.loads(raw_response.content)

        changed_view = TaxLotView.objects.exclude(state_id=tls_3).get()
        self.assertEqual(response['view_id'], changed_view.id)

        # Verify that taxlots 1 and 2 have been merged
        self.assertEqual(TaxLot.objects.count(), 2)
        self.assertEqual(TaxLotState.objects.count(), 5)  # Original 3 + 1 edit + 1 merge result
        self.assertEqual(TaxLotView.objects.count(), 2)

        # It will have a -State having city as Golden
        self.assertEqual(changed_view.state.city, 'Golden')

        # The corresponding log should be a System Match
        audit_log = TaxLotAuditLog.objects.get(state_id=changed_view.state_id)
        self.assertEqual(audit_log.name, 'System Match')

        # Update the edit and match-merge result -State
        new_data = {
            "state": {
                "jurisdiction_tax_lot_id": "1337AnotherDifferentID"
            }
        }
        url = reverse('api:v2:taxlots-detail', args=[changed_view.id]) + '?organization_id={}'.format(self.org.pk)
        raw_response = self.client.put(url, json.dumps(new_data), content_type='application/json')
        response = json.loads(raw_response.content)

        self.assertEqual(response['match_merged_count'], 2)

        # Verify that there's only 1 canonical TaxLot and View left
        self.assertEqual(TaxLot.objects.count(), 1)
        # 6 -States since, 5 from 1st round + 1 from merge
        # None created during edit since the audit log isn't named 'Import Creation'
        self.assertEqual(TaxLotState.objects.count(), 6)
        self.assertEqual(TaxLotView.objects.count(), 1)
        view = TaxLotView.objects.first()

        self.assertEqual(response['view_id'], view.id)

        # Check that city is still Golden, since the edited -State takes precedence
        self.assertEqual(view.state.city, 'Golden')


class TestMatchingPostMerge(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars

        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.client.login(**user_details)

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

    def test_match_merge_happens_after_property_merge(self):
        base_details = {
            'pm_property_id': '123MatchID',
            'city': 'Golden',
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create 4 non-matching properties where merging 1 and 2, will match 4
        ps_1 = self.property_state_factory.get_property_state(**base_details)

        del base_details['pm_property_id']
        base_details['address_line_1'] = '123 Match Street'
        base_details['city'] = 'Denver'
        ps_2 = self.property_state_factory.get_property_state(**base_details)

        # Property 3 is here to be sure it remains unchanged
        del base_details['address_line_1']
        base_details['pm_property_id'] = '1337AnotherDifferentID'
        base_details['city'] = 'Philadelphia'
        ps_3 = self.property_state_factory.get_property_state(**base_details)

        base_details['address_line_1'] = '123 Match Street'
        base_details['pm_property_id'] = '123MatchID'
        base_details['city'] = 'Colorado Springs'
        self.property_state_factory.get_property_state(**base_details)

        self.import_file.mapping_done = True
        self.import_file.save()
        match_buildings(self.import_file.id)

        # Make sure all 4 are separate
        self.assertEqual(Property.objects.count(), 4)
        self.assertEqual(PropertyState.objects.count(), 4)
        self.assertEqual(PropertyView.objects.count(), 4)

        # Merge -State 1 and 2 - which should then match merge with -State 4 with precedence to the initial merged -State
        url = reverse('api:v2:properties-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'state_ids': [ps_2.pk, ps_1.pk]
        })
        raw_response = self.client.post(url, post_params, content_type='application/json')
        response = json.loads(raw_response.content)

        self.assertEqual(response['match_merged_count'], 2)

        # Verify that 3 -States have been merged and 2 remain
        self.assertEqual(Property.objects.count(), 2)
        self.assertEqual(PropertyState.objects.count(), 6)  # Original 4 + 1 initial merge + 1 post merge
        self.assertEqual(PropertyView.objects.count(), 2)

        # Note, the success of the .get() implies the other View had state_id=ps_3
        changed_view = PropertyView.objects.exclude(state_id=ps_3).get()

        # It will have a -State having city as Golden
        self.assertEqual(changed_view.state.city, 'Golden')

        # The corresponding log should be a System Match
        audit_log = PropertyAuditLog.objects.get(state_id=changed_view.state_id)
        self.assertEqual(audit_log.name, 'System Match')

    def test_match_merge_happens_after_taxlot_merge(self):
        base_details = {
            'jurisdiction_tax_lot_id': '123MatchID',
            'city': 'Golden',
            'import_file_id': self.import_file.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create 4 non-matching taxlots where merging 1 and 2, will match 4
        tls_1 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        del base_details['jurisdiction_tax_lot_id']
        base_details['address_line_1'] = '123 Match Street'
        base_details['city'] = 'Denver'
        tls_2 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        # TaxLot 3 is here to be sure it remains unchanged
        del base_details['address_line_1']
        base_details['jurisdiction_tax_lot_id'] = '1337AnotherDifferentID'
        base_details['city'] = 'Philadelphia'
        tls_3 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        base_details['address_line_1'] = '123 Match Street'
        base_details['jurisdiction_tax_lot_id'] = '123MatchID'
        base_details['city'] = 'Colorado Springs'
        self.taxlot_state_factory.get_taxlot_state(**base_details)

        self.import_file.mapping_done = True
        self.import_file.save()
        match_buildings(self.import_file.id)

        # Make sure all 4 are separate
        self.assertEqual(TaxLot.objects.count(), 4)
        self.assertEqual(TaxLotState.objects.count(), 4)
        self.assertEqual(TaxLotView.objects.count(), 4)

        # Merge -State 1 and 2 - which should then match merge with -State 4 with precedence to the initial merged -State
        url = reverse('api:v2:taxlots-merge') + '?organization_id={}'.format(self.org.pk)
        post_params = json.dumps({
            'state_ids': [tls_2.pk, tls_1.pk]
        })
        raw_response = self.client.post(url, post_params, content_type='application/json')
        response = json.loads(raw_response.content)

        self.assertEqual(response['match_merged_count'], 2)

        # Verify that 3 -States have been merged and 2 remain
        self.assertEqual(TaxLot.objects.count(), 2)
        self.assertEqual(TaxLotState.objects.count(), 6)  # Original 4 + 1 initial merge + 1 post merge
        self.assertEqual(TaxLotView.objects.count(), 2)

        # Note, the success of the .get() implies the other View had state_id=tls_3
        changed_view = TaxLotView.objects.exclude(state_id=tls_3).get()

        # It will have a -State having city as Golden
        self.assertEqual(changed_view.state.city, 'Golden')

        # The corresponding log should be a System Match
        audit_log = TaxLotAuditLog.objects.get(state_id=changed_view.state_id)
        self.assertEqual(audit_log.name, 'System Match')


class TestMatchingExistingViewMatching(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file_1, self.import_record_1, self.cycle = selfvars

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

    def test_match_merge_in_cycle_rolls_up_existing_property_matches_in_id_order_if_they_exist_with_priority_given_to_selected_property(self):
        base_details = {
            'pm_property_id': '123MatchID',
            'city': 'Golden',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create 3 non-matching properties in first ImportFile
        ps_1 = self.property_state_factory.get_property_state(**base_details)

        base_details['pm_property_id'] = '789DifferentID'
        base_details['city'] = 'Denver'
        ps_2 = self.property_state_factory.get_property_state(**base_details)

        base_details['pm_property_id'] = '1337AnotherDifferentID'
        base_details['city'] = 'Philadelphia'
        ps_3 = self.property_state_factory.get_property_state(**base_details)

        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Verify no matches exist
        ps_1_view = PropertyView.objects.get(state_id=ps_1.id)
        count_result, no_match_indicator = match_merge_in_cycle(ps_1_view.id, 'PropertyState')
        self.assertEqual(count_result, 0)
        self.assertIsNone(no_match_indicator)

        # Make all those states match
        PropertyState.objects.filter(pk__in=[ps_2.id, ps_3.id]).update(
            pm_property_id='123MatchID'
        )

        # Verify that none of the 3 have been merged
        self.assertEqual(Property.objects.count(), 3)
        self.assertEqual(PropertyState.objects.count(), 3)
        self.assertEqual(PropertyView.objects.count(), 3)

        ps_1_view = PropertyView.objects.get(state_id=ps_1.id)
        count_result, view_id_result = match_merge_in_cycle(ps_1_view.id, 'PropertyState')
        self.assertEqual(count_result, 3)

        # There should only be one PropertyView which is associated to new, merged -State
        self.assertEqual(PropertyView.objects.count(), 1)
        view = PropertyView.objects.first()
        self.assertEqual(view_id_result, view.id)
        self.assertNotIn(view.state_id, [ps_1.id, ps_2.id, ps_3.id])

        # It will have a -State having city as Philadelphia
        self.assertEqual(view.state.city, 'Golden')

        # The corresponding log should be a System Match
        audit_log = PropertyAuditLog.objects.get(state_id=view.state_id)
        self.assertEqual(audit_log.name, 'System Match')

    def test_match_merge_in_cycle_ignores_properties_with_unpopulated_matching_criteria(self):
        base_details = {
            'city': 'Golden',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create 3 non-duplicate properties with unpopulated matching criteria
        ps_1 = self.property_state_factory.get_property_state(**base_details)

        base_details['city'] = 'Denver'
        ps_2 = self.property_state_factory.get_property_state(**base_details)

        base_details['city'] = 'Philadelphia'
        ps_3 = self.property_state_factory.get_property_state(**base_details)

        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Verify no match merges happen
        ps_1_view = PropertyView.objects.get(state_id=ps_1.id)
        count_result, no_match_indicator = match_merge_in_cycle(ps_1_view.id, 'PropertyState')
        self.assertEqual(count_result, 0)
        self.assertIsNone(no_match_indicator)

        self.assertEqual(Property.objects.count(), 3)
        self.assertEqual(PropertyState.objects.count(), 3)
        self.assertEqual(PropertyView.objects.count(), 3)

        state_ids = list(PropertyView.objects.all().values_list('state_id', flat=True))
        self.assertCountEqual([ps_1.id, ps_2.id, ps_3.id], state_ids)

    def test_match_merge_in_cycle_rolls_up_existing_taxlot_matches_in_id_order_if_they_exist_with_priority_given_to_selected_property(self):
        base_details = {
            'jurisdiction_tax_lot_id': '123MatchID',
            'city': 'Golden',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create 3 non-matching taxlots in first ImportFile
        tls_1 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        base_details['jurisdiction_tax_lot_id'] = '789DifferentID'
        base_details['city'] = 'Denver'
        tls_2 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        base_details['jurisdiction_tax_lot_id'] = '1337AnotherDifferentID'
        base_details['city'] = 'Philadelphia'
        tls_3 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Verify no matches exist
        tls_1_view = TaxLotView.objects.get(state_id=tls_1.id)
        count_result, no_match_indicator = match_merge_in_cycle(tls_1_view.id, 'TaxLotState')
        self.assertEqual(count_result, 0)
        self.assertIsNone(no_match_indicator)

        # Make all those states match
        TaxLotState.objects.filter(pk__in=[tls_2.id, tls_3.id]).update(
            jurisdiction_tax_lot_id='123MatchID'
        )

        # Verify that none of the 3 have been merged
        self.assertEqual(TaxLot.objects.count(), 3)
        self.assertEqual(TaxLotState.objects.count(), 3)
        self.assertEqual(TaxLotView.objects.count(), 3)

        count_result, view_id_result = match_merge_in_cycle(tls_1_view.id, 'TaxLotState')
        self.assertEqual(count_result, 3)

        # There should only be one TaxLotView which is associated to new, merged -State
        self.assertEqual(TaxLotView.objects.count(), 1)
        view = TaxLotView.objects.first()
        self.assertEqual(view_id_result, view.id)
        self.assertNotIn(view.state_id, [tls_1.id, tls_2.id, tls_3.id])

        # It will have a -State having city as Philadelphia
        self.assertEqual(view.state.city, 'Golden')

        # The corresponding log should be a System Match
        audit_log = TaxLotAuditLog.objects.get(state_id=view.state_id)
        self.assertEqual(audit_log.name, 'System Match')

    def test_match_merge_in_cycle_ignores_taxlots_with_unpopulated_matching_criteria(self):
        base_details = {
            'city': 'Golden',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create 3 non-duplicate taxlots with unpopulated matching criteria
        tls_1 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        base_details['city'] = 'Denver'
        tls_2 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        base_details['city'] = 'Philadelphia'
        tls_3 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Verify no match merges happen
        tls_1_view = TaxLotView.objects.get(state_id=tls_1.id)
        count_result, no_match_indicator = match_merge_in_cycle(tls_1_view.id, 'TaxLotState')
        self.assertEqual(count_result, 0)
        self.assertIsNone(no_match_indicator)

        self.assertEqual(TaxLot.objects.count(), 3)
        self.assertEqual(TaxLotState.objects.count(), 3)
        self.assertEqual(TaxLotView.objects.count(), 3)

        state_ids = list(TaxLotView.objects.all().values_list('state_id', flat=True))
        self.assertCountEqual([tls_1.id, tls_2.id, tls_3.id], state_ids)
