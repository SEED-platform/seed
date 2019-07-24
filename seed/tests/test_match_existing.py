# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import json

from django.core.urlresolvers import reverse
from django.db.models import Subquery

from seed.data_importer.tasks import match_buildings

from seed.models import (
    ASSESSED_RAW,
    DATA_STATE_MAPPING,
    Column,
    Property,
    PropertyAuditLog,
    PropertyState,
    PropertyView,
    TaxLot,
    TaxLotAuditLog,
    TaxLotState,
    TaxLotView,
)
from seed.utils.match import (
    match_merge_in_cycle,
    whole_org_match_merge_link,
)
from seed.test_helpers.fake import (
    FakeCycleFactory,
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

        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.client.login(**user_details)

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

    def test_match_merge_in_cycle_rolls_up_existing_property_matches_in_updated_state_order_with_final_priority_given_to_selected_property(self):
        """
        Import 4 non-matching records each with different cities and
        state_orders (extra data field).

        Create a Column record for state_orders, and update merge protection
        setting for the city column.

        Change the 'updated' field's datetime value for each -State. Use
        update() to make the records match to avoid changing the 'updated'
        values. Run merging and unmerge records to unravel and reveal the merge
        order.
        """
        base_details = {
            'pm_property_id': '123MatchID',
            'city': '1st Oldest City',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
            'extra_data': {
                'state_order': 'first',
            },
        }
        ps_1 = self.property_state_factory.get_property_state(**base_details)

        base_details['pm_property_id'] = '123DifferentID'
        base_details['city'] = '2nd Oldest City'
        base_details['extra_data']['state_order'] = 'second'
        ps_2 = self.property_state_factory.get_property_state(**base_details)

        base_details['pm_property_id'] = '456DifferentID'
        base_details['city'] = '3rd Oldest City'
        base_details['extra_data']['state_order'] = 'third'
        ps_3 = self.property_state_factory.get_property_state(**base_details)

        base_details['pm_property_id'] = '789DifferentID'
        base_details['city'] = '4th Oldest City'
        base_details['extra_data']['state_order'] = 'fourth'
        ps_4 = self.property_state_factory.get_property_state(**base_details)

        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Create (ED) 'state_order' column and update merge protection column for 'city'
        self.org.column_set.create(
            column_name='state_order',
            is_extra_data=True,
            table_name='PropertyState',
            merge_protection=Column.COLUMN_MERGE_FAVOR_EXISTING
        )
        self.org.column_set.filter(
            column_name='city',
            table_name='PropertyState'
        ).update(merge_protection=Column.COLUMN_MERGE_FAVOR_EXISTING)

        # Update -States to make the roll up order be 4, 2, 3
        refreshed_ps_4 = PropertyState.objects.get(id=ps_4.id)
        refreshed_ps_4.pm_property_id = '123MatchID'
        refreshed_ps_4.save()

        refreshed_ps_2 = PropertyState.objects.get(id=ps_2.id)
        refreshed_ps_2.pm_property_id = '123MatchID'
        refreshed_ps_2.save()

        refreshed_ps_3 = PropertyState.objects.get(id=ps_3.id)
        refreshed_ps_3.pm_property_id = '123MatchID'
        refreshed_ps_3.save()

        # run match_merge_in_cycle giving
        manual_merge_view = PropertyView.objects.get(state_id=ps_1.id)
        count_result, view_id_result = match_merge_in_cycle(manual_merge_view.id, 'PropertyState')
        self.assertEqual(count_result, 4)

        """
        Verify everything's rolled up to one -View with precedence given to
        manual merge -View with '1st Oldest City'. '1st Oldest City' is expected
        to be final City value since this rollup should ignore Merge Protection.
        """
        self.assertEqual(PropertyView.objects.count(), 1)
        only_view = PropertyView.objects.get()
        self.assertEqual(only_view.state.city, '1st Oldest City')
        self.assertEqual(only_view.state.extra_data['state_order'], 'first')

        """
        Undoing 1 rollup merge should expose a set -State having
        '3rd Oldest City' and state_order of 'third'.
        """
        rollback_unmerge_url_1 = reverse('api:v2:properties-unmerge', args=[only_view.id]) + '?organization_id={}'.format(self.org.pk)
        self.client.post(rollback_unmerge_url_1, content_type='application/json')

        rollback_view_1 = PropertyView.objects.prefetch_related('state').exclude(state__city='1st Oldest City').get()
        self.assertEqual(rollback_view_1.state.city, '3rd Oldest City')
        self.assertEqual(rollback_view_1.state.extra_data['state_order'], 'third')

        """
        Undoing another rollup merge should expose a set -State having
        '2nd Oldest City' and state_order of 'second'.
        """
        rollback_unmerge_url_2 = reverse('api:v2:properties-unmerge', args=[rollback_view_1.id]) + '?organization_id={}'.format(self.org.pk)
        self.client.post(rollback_unmerge_url_2, content_type='application/json')

        rollback_view_2 = PropertyView.objects.prefetch_related('state').exclude(state__city__in=['1st Oldest City', '3rd Oldest City']).get()
        self.assertEqual(rollback_view_2.state.city, '2nd Oldest City')
        self.assertEqual(rollback_view_2.state.extra_data['state_order'], 'second')

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

    def test_match_merge_in_cycle_rolls_up_existing_taxlot_matches_in_updated_state_order_with_final_priority_given_to_selected_taxlot(self):
        """
        Import 4 non-matching records each with different cities and
        state_orders (extra data field).

        Create a Column record for state_orders, and update merge protection
        setting for the city column.

        Change the 'updated' field's datetime value for each -State. Use
        update() to make the records match to avoid changing the 'updated'
        values. Run merging and unmerge records to unravel and reveal the merge
        order.
        """
        base_details = {
            'jurisdiction_tax_lot_id': '123MatchID',
            'city': '1st Oldest City',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
            'extra_data': {
                'state_order': 'first',
            },
        }
        tls_1 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        base_details['jurisdiction_tax_lot_id'] = '123DifferentID'
        base_details['city'] = '2nd Oldest City'
        base_details['extra_data']['state_order'] = 'second'
        tls_2 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        base_details['jurisdiction_tax_lot_id'] = '456DifferentID'
        base_details['city'] = '3rd Oldest City'
        base_details['extra_data']['state_order'] = 'third'
        tls_3 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        base_details['jurisdiction_tax_lot_id'] = '789DifferentID'
        base_details['city'] = '4th Oldest City'
        base_details['extra_data']['state_order'] = 'fourth'
        tls_4 = self.taxlot_state_factory.get_taxlot_state(**base_details)

        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Create (ED) 'state_order' column and update merge protection column for 'city'
        self.org.column_set.create(
            column_name='state_order',
            is_extra_data=True,
            table_name='TaxLotState',
            merge_protection=Column.COLUMN_MERGE_FAVOR_EXISTING
        )
        self.org.column_set.filter(
            column_name='city',
            table_name='TaxLotState'
        ).update(merge_protection=Column.COLUMN_MERGE_FAVOR_EXISTING)

        # Update -States to make the roll up order be 4, 2, 3
        refreshed_tls_4 = TaxLotState.objects.get(id=tls_4.id)
        refreshed_tls_4.jurisdiction_tax_lot_id = '123MatchID'
        refreshed_tls_4.save()

        refreshed_tls_2 = TaxLotState.objects.get(id=tls_2.id)
        refreshed_tls_2.jurisdiction_tax_lot_id = '123MatchID'
        refreshed_tls_2.save()

        refreshed_tls_3 = TaxLotState.objects.get(id=tls_3.id)
        refreshed_tls_3.jurisdiction_tax_lot_id = '123MatchID'
        refreshed_tls_3.save()

        # run match_merge_in_cycle giving
        manual_merge_view = TaxLotView.objects.get(state_id=tls_1.id)
        count_result, view_id_result = match_merge_in_cycle(manual_merge_view.id, 'TaxLotState')
        self.assertEqual(count_result, 4)

        """
        Verify everything's rolled up to one -View with precedence given to
        manual merge -View with '1st Oldest City'. '1st Oldest City' is expected
        to be final City value since this rollup should ignore Merge Protection.
        """
        self.assertEqual(TaxLotView.objects.count(), 1)
        only_view = TaxLotView.objects.get()
        self.assertEqual(only_view.state.city, '1st Oldest City')
        self.assertEqual(only_view.state.extra_data['state_order'], 'first')

        """
        Undoing 1 rollup merge should expose a set -State having
        '3rd Oldest City' and state_order of 'third'.
        """
        rollback_unmerge_url_1 = reverse('api:v2:taxlots-unmerge', args=[only_view.id]) + '?organization_id={}'.format(self.org.pk)
        self.client.post(rollback_unmerge_url_1, content_type='application/json')

        rollback_view_1 = TaxLotView.objects.prefetch_related('state').exclude(state__city='1st Oldest City').get()
        self.assertEqual(rollback_view_1.state.city, '3rd Oldest City')
        self.assertEqual(rollback_view_1.state.extra_data['state_order'], 'third')

        """
        Undoing another rollup merge should expose a set -State having
        '2nd Oldest City' and state_order of 'second'.
        """
        rollback_unmerge_url_2 = reverse('api:v2:taxlots-unmerge', args=[rollback_view_1.id]) + '?organization_id={}'.format(self.org.pk)
        self.client.post(rollback_unmerge_url_2, content_type='application/json')

        rollback_view_2 = TaxLotView.objects.prefetch_related('state').exclude(state__city__in=['1st Oldest City', '3rd Oldest City']).get()
        self.assertEqual(rollback_view_2.state.city, '2nd Oldest City')
        self.assertEqual(rollback_view_2.state.extra_data['state_order'], 'second')

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


class TestMatchingExistingViewFullOrgMatching(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file_1, self.import_record_1, self.cycle_1 = selfvars

        cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.cycle_2 = cycle_factory.get_cycle(name="Cycle 2")
        self.import_record_2, self.import_file_2 = self.create_import_file(
            self.user, self.org, self.cycle_2
        )

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

    def test_whole_org_match_merge_link(self):
        """
        The set up for this test is lengthy and includes multiple Property sets
        and TaxLot sets across multiple Cycles. In this context, a "set"
        includes a -State, -View, and canonical record.

        Cycle 1 - 6 property & 6 taxlot sets total will be created.
        For each (property and taxlot):
            - 2 sets match each other
            - 2 other sets match each other
            - 1 set doesn't match
            - 1 set doesn't match but links
        Cycle 2 - 6 property & 6 taxlot sets total will be created.
        For each (property and taxlot):
            - 3 sets match
            - 2 sets w/ null fields (won't merge or link)
            - 1 set doesn't match but links
        """
        # Cycle 1 / ImportFile 1
        base_property_details = {
            'pm_property_id': '1st Match Set',
            'city': 'Golden',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create 6 initially non-matching properties in first Cycle
        ps_11 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['pm_property_id'] = 'To be updated - 1st Match Set'
        base_property_details['city'] = 'Denver'
        ps_12 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['pm_property_id'] = '2nd Match Set'
        base_property_details['city'] = 'Philadelphia'
        ps_13 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['pm_property_id'] = 'To be updated - 2nd Match Set'
        base_property_details['city'] = 'Colorado Springs'
        ps_14 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['pm_property_id'] = 'Single Unmatched'
        base_property_details['city'] = 'Grand Junction'
        ps_15 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['pm_property_id'] = 'Single to be Linked!'
        base_property_details['city'] = 'Estes Park'
        ps_16 = self.property_state_factory.get_property_state(**base_property_details)

        base_taxlot_details = {
            'jurisdiction_tax_lot_id': '1st Match Set',
            'city': 'Golden',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create 6 initially non-matching taxlots in first Cycle
        tls_11 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        base_taxlot_details['jurisdiction_tax_lot_id'] = 'To be updated - 1st Match Set'
        base_taxlot_details['city'] = 'Denver'
        tls_12 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        base_taxlot_details['jurisdiction_tax_lot_id'] = '2nd Match Set'
        base_taxlot_details['city'] = 'Philadelphia'
        tls_13 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        base_taxlot_details['jurisdiction_tax_lot_id'] = 'To be updated - 2nd Match Set'
        base_taxlot_details['city'] = 'Colorado Springs'
        tls_14 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        base_taxlot_details['jurisdiction_tax_lot_id'] = 'Single Unmatched'
        base_taxlot_details['city'] = 'Grand Junction'
        tls_15 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        base_taxlot_details['jurisdiction_tax_lot_id'] = 'Single to be Linked!'
        base_taxlot_details['city'] = 'Estes Park'
        tls_16 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        # Import file and create -Views and canonical records.
        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Make some match but don't trigger matching round
        PropertyState.objects.filter(pk=ps_12.id).update(pm_property_id='1st Match Set')
        PropertyState.objects.filter(pk=ps_14.id).update(pm_property_id='2nd Match Set')
        TaxLotState.objects.filter(pk=tls_12.id).update(jurisdiction_tax_lot_id='1st Match Set')
        TaxLotState.objects.filter(pk=tls_14.id).update(jurisdiction_tax_lot_id='2nd Match Set')

        # Check all property and taxlot sets were created without match merges
        self.assertEqual(6, Property.objects.count())
        self.assertEqual(6, PropertyState.objects.count())
        self.assertEqual(6, PropertyView.objects.count())
        self.assertEqual(6, TaxLot.objects.count())
        self.assertEqual(6, TaxLotState.objects.count())
        self.assertEqual(6, TaxLotView.objects.count())

        # Cycle 2 / ImportFile 2
        base_property_details = {
            'pm_property_id': '1st Match Set',
            'city': 'Golden',
            'import_file_id': self.import_file_2.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create 6 initially non-matching properties in second Cycle
        ps_21 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['pm_property_id'] = 'To be updated 1 - 1st Match Set'
        base_property_details['city'] = 'Denver'
        ps_22 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['pm_property_id'] = 'To be updated 2 - 1st Match Set'
        base_property_details['city'] = 'Philadelphia'
        ps_23 = self.property_state_factory.get_property_state(**base_property_details)

        del base_property_details['pm_property_id']
        base_property_details['city'] = 'Null Fields 1'
        ps_24 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['city'] = 'Null Fields 2'
        ps_25 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['pm_property_id'] = 'Single to be Linked! - will be updated later'
        base_property_details['city'] = 'Estes Park'
        ps_26 = self.property_state_factory.get_property_state(**base_property_details)

        base_taxlot_details = {
            'jurisdiction_tax_lot_id': '1st Match Set',
            'city': 'Golden',
            'import_file_id': self.import_file_2.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create 6 initially non-matching taxlots in second Cycle
        tls_21 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        base_taxlot_details['jurisdiction_tax_lot_id'] = 'To be updated 1 - 1st Match Set'
        base_taxlot_details['city'] = 'Denver'
        tls_22 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        base_taxlot_details['jurisdiction_tax_lot_id'] = 'To be updated 2 - 1st Match Set'
        base_taxlot_details['city'] = 'Philadelphia'
        tls_23 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        del base_taxlot_details['jurisdiction_tax_lot_id']
        base_taxlot_details['city'] = 'Null Fields 1'
        tls_24 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        base_taxlot_details['city'] = 'Null Fields 2'
        tls_25 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        base_taxlot_details['jurisdiction_tax_lot_id'] = 'Single to be Linked! - will be updated later'
        base_taxlot_details['city'] = 'Estes Park'
        tls_26 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        # Import file and create -Views and canonical records.
        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        match_buildings(self.import_file_2.id)

        # Make some match but don't trigger matching round
        PropertyState.objects.filter(pk__in=[ps_22.id, ps_23.id]).update(pm_property_id='1st Match Set')
        TaxLotState.objects.filter(pk__in=[tls_22.id, tls_23.id]).update(jurisdiction_tax_lot_id='1st Match Set')

        PropertyState.objects.filter(pk=ps_26.id).update(pm_property_id='Single to be Linked!')
        TaxLotState.objects.filter(pk=tls_26.id).update(jurisdiction_tax_lot_id='Single to be Linked!')

        # Check all property and taxlot sets were created without match merges
        self.assertEqual(12, Property.objects.count())
        self.assertEqual(12, PropertyState.objects.count())
        self.assertEqual(12, PropertyView.objects.count())
        self.assertEqual(12, TaxLot.objects.count())
        self.assertEqual(12, TaxLotState.objects.count())
        self.assertEqual(12, TaxLotView.objects.count())

        # Capture initial canonical IDs of impending matches - used for tests
        initial_property_ids_of_matches = list(
            PropertyView.objects.
            select_related('state').
            filter(state__pm_property_id__in=['1st Match Set', '2nd Match Set', 'Single to be Linked!']).
            values_list('property_id', flat=True)
        )
        initial_taxlot_ids_of_matches = list(
            TaxLotView.objects.
            select_related('state').
            filter(state__jurisdiction_tax_lot_id__in=['1st Match Set', '2nd Match Set', 'Single to be Linked!']).
            values_list('taxlot_id', flat=True)
        )

        summary = whole_org_match_merge_link(self.org.id)

        """
        Now that the set up is complete, test the state of both property and
        taxlot records.

        The matching field being looked at for each record type is as follows:
        property ==> pm_property_id
        taxlot ==> jurisdiction_tax_lot_id

        Merges:
            Within Cycle 1,
                - The 2 -States with '1st Match Set' are merged together
                - The 2 -States with '2nd Match Set' are merged together
                - The other 2 -States were not merged.

            Within Cycle 2,
                - The 3 -States with '1st Match Set' are merged together
                - The other 3 -States are unchanged.

        Links:
            Between both Cycles, links via canonical ID on -Views are established.
                - The resulting merged -States from each Cycle with '1st Match Set'
                - The -State from each Cycle with 'Single to be Linked!'
        """

        # Check -View counts
        # 8 = 12 - 2 [merged in Cycle 1] - 2 [merged in Cycle 2]
        self.assertEqual(8, PropertyView.objects.count())
        self.assertEqual(8, TaxLotView.objects.count())

        # Check canonical record counts
        # 6 = 12 - 2 [merged in Cycle 1] - 2 [merged in Cycle 2] - 2 [deleted and unused since link was created]
        self.assertEqual(6, Property.objects.count())
        self.assertEqual(6, TaxLot.objects.count())

        # Check that previous canonical records that were merged and/or linked are no longer used
        self.assertFalse(Property.objects.filter(pk__in=initial_property_ids_of_matches).exists())
        self.assertFalse(TaxLot.objects.filter(pk__in=initial_taxlot_ids_of_matches).exists())

        # Check that a link was created for -States across Cycles
        # Specifically, canonical IDs should match but cycles should be different
        property_first_match_set = PropertyState.objects.filter(pm_property_id='1st Match Set')
        link_p_11, link_p_12 = PropertyView.objects.filter(state_id__in=Subquery(property_first_match_set.values('id'))).values('cycle_id', 'property_id')
        self.assertEqual(link_p_11['property_id'], link_p_12['property_id'])
        self.assertNotEqual(link_p_11['cycle_id'], link_p_12['cycle_id'])

        property_single_linked = PropertyState.objects.filter(pm_property_id='Single to be Linked!')
        link_p_21, link_p_22 = PropertyView.objects.filter(state_id__in=Subquery(property_single_linked.values('id'))).values('cycle_id', 'property_id')
        self.assertEqual(link_p_21['property_id'], link_p_22['property_id'])
        self.assertNotEqual(link_p_21['cycle_id'], link_p_22['cycle_id'])

        taxlot_first_match_set = TaxLotState.objects.filter(jurisdiction_tax_lot_id='1st Match Set')
        link_tl_11, link_tl_12 = TaxLotView.objects.filter(state_id__in=Subquery(taxlot_first_match_set.values('id'))).values('cycle_id', 'taxlot_id')
        self.assertEqual(link_tl_11['taxlot_id'], link_tl_12['taxlot_id'])
        self.assertNotEqual(link_tl_11['cycle_id'], link_tl_12['cycle_id'])

        taxlot_single_linked = TaxLotState.objects.filter(jurisdiction_tax_lot_id='Single to be Linked!')
        link_tl_11, link_tl_12 = TaxLotView.objects.filter(state_id__in=Subquery(taxlot_single_linked.values('id'))).values('cycle_id', 'taxlot_id')
        self.assertEqual(link_tl_11['taxlot_id'], link_tl_12['taxlot_id'])
        self.assertNotEqual(link_tl_11['cycle_id'], link_tl_12['cycle_id'])

        # Check -State counts
        # 16 = 12 + 2 [Cycle 1 merges] + 2 [Cycle 2 merges]
        self.assertEqual(16, TaxLotState.objects.count())
        self.assertEqual(16, PropertyState.objects.count())

        # Check -States part of merges are no longer associated to -Views
        merged_ps_ids = [
            ps_11.id, ps_12.id,  # Cycle 1
            ps_13.id, ps_14.id,  # Cycle 1
            ps_21.id, ps_22.id, ps_23.id  # Cycle 2
        ]
        self.assertFalse(PropertyView.objects.filter(state_id__in=merged_ps_ids).exists())

        merged_tls_ids = [
            tls_11.id, tls_12.id,  # Cycle 1
            tls_13.id, tls_14.id,  # Cycle 1
            tls_21.id, tls_22.id, tls_23.id  # Cycle 2
        ]
        self.assertFalse(TaxLotView.objects.filter(state_id__in=merged_tls_ids).exists())

        # Check -States NOT part of merges are still associated to -Views
        self.assertTrue(PropertyView.objects.filter(state_id=ps_15.id).exists())
        self.assertTrue(PropertyView.objects.filter(state_id=ps_16.id).exists())

        self.assertTrue(PropertyView.objects.filter(state_id=ps_24.id).exists())
        self.assertTrue(PropertyView.objects.filter(state_id=ps_25.id).exists())
        self.assertTrue(PropertyView.objects.filter(state_id=ps_26.id).exists())

        self.assertTrue(TaxLotView.objects.filter(state_id=tls_15.id).exists())
        self.assertTrue(TaxLotView.objects.filter(state_id=tls_16.id).exists())

        self.assertTrue(TaxLotView.objects.filter(state_id=tls_24.id).exists())
        self.assertTrue(TaxLotView.objects.filter(state_id=tls_25.id).exists())
        self.assertTrue(TaxLotView.objects.filter(state_id=tls_26.id).exists())

        """
        Check Merges occurred correctly, with priority given to most recently
        updated or, in this case, newer -States as evidenced by 'city' values
        Each Cycle should have 4 PropertyStates and 4 TaxLotStates with unique cities in each Cycle.
        """
        cycle_1_pviews = PropertyView.objects.filter(cycle_id=self.cycle_1.id)
        cycle_1_pstates = PropertyState.objects.filter(pk__in=Subquery(cycle_1_pviews.values('state_id')))

        self.assertEqual(4, cycle_1_pstates.count())
        self.assertEqual(1, cycle_1_pstates.filter(city='Denver').count())
        self.assertEqual(1, cycle_1_pstates.filter(city='Colorado Springs').count())
        self.assertEqual(1, cycle_1_pstates.filter(city='Grand Junction').count())
        self.assertEqual(1, cycle_1_pstates.filter(city='Estes Park').count())

        cycle_2_pviews = PropertyView.objects.filter(cycle_id=self.cycle_2.id)
        cycle_2_pstates = PropertyState.objects.filter(pk__in=Subquery(cycle_2_pviews.values('state_id')))

        self.assertEqual(4, cycle_2_pstates.count())
        self.assertEqual(1, cycle_2_pstates.filter(city='Philadelphia').count())
        self.assertEqual(1, cycle_2_pstates.filter(city='Null Fields 1').count())
        self.assertEqual(1, cycle_2_pstates.filter(city='Null Fields 2').count())
        self.assertEqual(1, cycle_2_pstates.filter(city='Estes Park').count())

        cycle_1_tlviews = TaxLotView.objects.filter(cycle_id=self.cycle_1.id)
        cycle_1_tlstates = TaxLotState.objects.filter(pk__in=Subquery(cycle_1_tlviews.values('state_id')))

        self.assertEqual(4, cycle_1_tlstates.count())
        self.assertEqual(1, cycle_1_tlstates.filter(city='Denver').count())
        self.assertEqual(1, cycle_1_tlstates.filter(city='Colorado Springs').count())
        self.assertEqual(1, cycle_1_tlstates.filter(city='Grand Junction').count())
        self.assertEqual(1, cycle_1_tlstates.filter(city='Estes Park').count())

        cycle_2_tlviews = TaxLotView.objects.filter(cycle_id=self.cycle_2.id)
        cycle_2_tlstates = TaxLotState.objects.filter(pk__in=Subquery(cycle_2_tlviews.values('state_id')))

        self.assertEqual(4, cycle_2_tlstates.count())
        self.assertEqual(1, cycle_2_tlstates.filter(city='Philadelphia').count())
        self.assertEqual(1, cycle_2_tlstates.filter(city='Null Fields 1').count())
        self.assertEqual(1, cycle_2_tlstates.filter(city='Null Fields 2').count())
        self.assertEqual(1, cycle_2_tlstates.filter(city='Estes Park').count())

        # Finally, check method returned expected summary
        expected_summary = {
            'PropertyState': {
                'merged_count': 7,
                'linked_sets_count': 2,
            },
            'TaxLotState': {
                'merged_count': 7,
                'linked_sets_count': 2,
            },
        }

        self.assertEqual(
            summary['PropertyState']['merged_count'],
            expected_summary['PropertyState']['merged_count']
        )
        self.assertEqual(
            summary['TaxLotState']['merged_count'],
            expected_summary['TaxLotState']['merged_count']
        )

        self.assertEqual(
            summary['PropertyState']['linked_sets_count'],
            expected_summary['PropertyState']['linked_sets_count']
        )
        self.assertEqual(
            summary['TaxLotState']['linked_sets_count'],
            expected_summary['TaxLotState']['linked_sets_count']
        )
