# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import json

from config.settings.common import TIME_ZONE

from datetime import datetime

from django.contrib.postgres.aggregates.general import ArrayAgg
from django.urls import reverse
from django.db.models.aggregates import Count
from django.db.models import Subquery
from django.utils.timezone import make_aware  # make_aware is used because inconsistencies exist in creating datetime with tzinfo

from pytz import timezone

from seed.data_importer.tasks import match_buildings

from seed.models import (
    ASSESSED_RAW,
    DATA_STATE_MAPPING,
    Column,
    Meter,
    MeterReading,
    Property,
    PropertyAuditLog,
    PropertyState,
    PropertyView,
    TaxLot,
    TaxLotAuditLog,
    TaxLotState,
    TaxLotView,
    VIEW_LIST_TAXLOT,
)
from seed.utils.match import (
    match_merge_link,
    whole_org_match_merge_link,
)
from seed.test_helpers.fake import (
    FakeColumnListSettingsFactory,
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

    def test_match_merge_link_rolls_up_existing_property_matches_in_updated_state_order_with_final_priority_given_to_selected_property(self):
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

        # run match_merge_link giving
        manual_merge_view = PropertyView.objects.get(state_id=ps_1.id)
        count_result, _link_count, view_id_result = match_merge_link(manual_merge_view.id, 'PropertyState')
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

    def test_match_merge_link_ignores_properties_with_unpopulated_matching_criteria(self):
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
        count_result, _link_count, no_match_indicator = match_merge_link(ps_1_view.id, 'PropertyState')
        self.assertEqual(count_result, 0)
        self.assertIsNone(no_match_indicator)

        self.assertEqual(Property.objects.count(), 3)
        self.assertEqual(PropertyState.objects.count(), 3)
        self.assertEqual(PropertyView.objects.count(), 3)

        state_ids = list(PropertyView.objects.all().values_list('state_id', flat=True))
        self.assertCountEqual([ps_1.id, ps_2.id, ps_3.id], state_ids)

    def test_match_merge_link_rolls_up_existing_taxlot_matches_in_updated_state_order_with_final_priority_given_to_selected_taxlot(self):
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

        # run match_merge_link giving
        manual_merge_view = TaxLotView.objects.get(state_id=tls_1.id)
        count_result, _link_count, view_id_result = match_merge_link(manual_merge_view.id, 'TaxLotState')
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

    def test_match_merge_link_ignores_taxlots_with_unpopulated_matching_criteria(self):
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
        count_result, _link_count, no_match_indicator = match_merge_link(tls_1_view.id, 'TaxLotState')
        self.assertEqual(count_result, 0)
        self.assertIsNone(no_match_indicator)

        self.assertEqual(TaxLot.objects.count(), 3)
        self.assertEqual(TaxLotState.objects.count(), 3)
        self.assertEqual(TaxLotView.objects.count(), 3)

        state_ids = list(TaxLotView.objects.all().values_list('state_id', flat=True))
        self.assertCountEqual([tls_1.id, tls_2.id, tls_3.id], state_ids)


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

        Set up consists of: (None will be merged or linked on import)
        Cycle 1 - 3 property sets will be created.
            - 2 sets match each other but unmerged
            - 1 set doesn't match any others
        Cycle 2 - 4 property sets will be created.
            - 3 sets match but unmerged, all will merge then link to 2 sets in Cycle 1
            - 1 set doesn't match any others
        Cycle 3 - 2 property sets will be created.
            - 1 set will match link to sets from Cycles 1 and 2
            - 1 set doesn't match any others
        """
        # Cycle 1 / ImportFile 1
        base_property_details = {
            'pm_property_id': '1st Match Set',
            'city': '1st Match - Cycle 1 - City 1',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        ps_11 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['pm_property_id'] = 'To be updated - Cycle 1 - 1st Match Set'
        base_property_details['city'] = '1st Match - Cycle 1 - City 2'
        ps_12 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['pm_property_id'] = 'Single Unmatched - 1'
        base_property_details['city'] = 'Unmatched City - Cycle 1'
        ps_13 = self.property_state_factory.get_property_state(**base_property_details)

        # Import file and create -Views and canonical records.
        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Cycle 2 / ImportFile 2
        base_property_details['import_file_id'] = self.import_file_2.id
        base_property_details['pm_property_id'] = 'To be updated - Cycle 2 - 1st Match Set'
        base_property_details['city'] = '1st Match - Cycle 2 - City 1'
        ps_21 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['pm_property_id'] = '2nd to be updated - Cycle 2 - 1st Match Set'
        base_property_details['city'] = '1st Match - Cycle 2 - City 2'
        ps_22 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['pm_property_id'] = '3rd to be updated - Cycle 2 - 1st Match Set'
        base_property_details['city'] = '1st Match - Cycle 2 - City 3'
        ps_23 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['pm_property_id'] = 'Single Unmatched - 2'
        base_property_details['city'] = 'Unmatched City - Cycle 2'
        ps_24 = self.property_state_factory.get_property_state(**base_property_details)

        # Import file and create -Views and canonical records.
        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        match_buildings(self.import_file_2.id)

        # Cycle 3 / ImportFile 3
        base_property_details['import_file_id'] = self.import_file_3.id
        base_property_details['pm_property_id'] = 'To be updated - Cycle 3 - 1st Match Set'
        base_property_details['city'] = '1st Match - Cycle 3 - City 1'
        ps_31 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['pm_property_id'] = 'Single Unmatched - 3'
        base_property_details['city'] = 'Unmatched City - Cycle 3'
        ps_32 = self.property_state_factory.get_property_state(**base_property_details)

        # Import file and create -Views and canonical records.
        self.import_file_3.mapping_done = True
        self.import_file_3.save()
        match_buildings(self.import_file_3.id)

        # Verify no matches or links
        self.assertEqual(9, PropertyView.objects.count())
        self.assertEqual(9, PropertyState.objects.count())
        self.assertEqual(9, Property.objects.count())

        # At the moment, no two -Views have the same canonical records
        views_with_same_canonical_records = PropertyView.objects.\
            values('property_id').\
            annotate(times_used=Count('id')).\
            filter(times_used__gt=1)
        self.assertFalse(views_with_same_canonical_records.exists())

        # (Unrealistically) Make some match
        to_be_matched_ids = [
            ps_12.id,  # Cycle 1
            ps_21.id, ps_22.id, ps_23.id,  # Cycle 2
            ps_31.id,  # Cycle 3
        ]
        PropertyState.objects.filter(id__in=to_be_matched_ids).update(pm_property_id='1st Match Set')

        # Give ps_22 priority in Cycle 2
        refreshed_ps_22 = PropertyState.objects.get(id=ps_22.id)
        refreshed_ps_22.save()

        # run match_merge_link on Sets that WON'T trigger merges or linkings
        match_merge_link(PropertyView.objects.get(state_id=ps_13.id).id, 'PropertyState')
        match_merge_link(PropertyView.objects.get(state_id=ps_24.id).id, 'PropertyState')
        match_merge_link(PropertyView.objects.get(state_id=ps_32.id).id, 'PropertyState')
        self.assertEqual(9, PropertyView.objects.count())
        self.assertEqual(9, PropertyState.objects.count())
        self.assertEqual(9, Property.objects.count())

        # run match_merge_link on a Set that WILL trigger merges and linkings
        target_view = PropertyView.objects.get(state_id=ps_11.id)
        merge_count, link_count, _view_id = match_merge_link(target_view.id, 'PropertyState')

        self.assertEqual(5, merge_count)
        self.assertEqual(2, link_count)

        # Check merges by Cycle - use cities to check merge precedence order
        # Cycle 1
        cycle_1_views = PropertyView.objects.filter(cycle_id=self.cycle_1.id)
        self.assertEqual(2, cycle_1_views.count())

        cycle_1_cities = list(cycle_1_views.prefetch_related('state').values_list('state__city', flat=True))
        expected_cities_1 = [
            '1st Match - Cycle 1 - City 1',  # ps_11 took precedence over ps_12, since the provided -View was ps_11's -View
            'Unmatched City - Cycle 1'
        ]
        self.assertCountEqual(expected_cities_1, cycle_1_cities)

        # Cycle 2
        cycle_2_views = PropertyView.objects.filter(cycle_id=self.cycle_2.id)
        self.assertEqual(2, cycle_2_views.count())

        cycle_2_cities = list(cycle_2_views.prefetch_related('state').values_list('state__city', flat=True))
        expected_cities_2 = [
            '1st Match - Cycle 2 - City 2',  # ps_22 was explicitly given precedence
            'Unmatched City - Cycle 2'
        ]
        self.assertCountEqual(expected_cities_2, cycle_2_cities)

        # Cycle 3 - No merges
        cycle_3_views = PropertyView.objects.filter(cycle_id=self.cycle_3.id)
        self.assertEqual(2, cycle_3_views.count())

        # Check links
        views_by_canonical_record = PropertyView.objects.\
            values('property_id').\
            annotate(view_ids=ArrayAgg('id'), times_used=Count('id'))
        self.assertTrue(views_by_canonical_record.filter(times_used__gt=1).exists())

        # For linked views, the corresponding -States should match
        # In this case, all should have the same pm_property_id.
        for view_ids in views_by_canonical_record.values_list('view_ids', flat=True):
            base_state = PropertyView.objects.get(id=view_ids[0]).state
            matching_view_ids = list(
                PropertyView.objects.
                prefetch_related('state').
                filter(state__pm_property_id=base_state.pm_property_id).
                values_list('id', flat=True)
            )
            self.assertCountEqual(view_ids, matching_view_ids)

    def test_match_merge_link_for_taxlots(self):
        """
        In this context, a "set" includes a -State, -View, and canonical record.

        Set up consists of: (None will be merged or linked on import)
        Cycle 1 - 3 taxlot sets will be created.
            - 2 sets match each other but unmerged
            - 1 set doesn't match any others
        Cycle 2 - 4 taxlot sets will be created.
            - 3 sets match but unmerged, all will merge then link to 2 sets in Cycle 1
            - 1 set doesn't match any others
        Cycle 3 - 2 taxlot sets will be created.
            - 1 set will match link to sets from Cycles 1 and 2
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
        tls_11 = self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        base_state_details['jurisdiction_tax_lot_id'] = 'To be updated - Cycle 1 - 1st Match Set'
        base_state_details['city'] = '1st Match - Cycle 1 - City 2'
        tls_12 = self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        base_state_details['jurisdiction_tax_lot_id'] = 'Single Unmatched - 1'
        base_state_details['city'] = 'Unmatched City - Cycle 1'
        tls_13 = self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        # Import file and create -Views and canonical records.
        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Cycle 2 / ImportFile 2
        base_state_details['import_file_id'] = self.import_file_2.id
        base_state_details['jurisdiction_tax_lot_id'] = 'To be updated - Cycle 2 - 1st Match Set'
        base_state_details['city'] = '1st Match - Cycle 2 - City 1'
        tls_21 = self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        base_state_details['jurisdiction_tax_lot_id'] = '2nd to be updated - Cycle 2 - 1st Match Set'
        base_state_details['city'] = '1st Match - Cycle 2 - City 2'
        tls_22 = self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        base_state_details['jurisdiction_tax_lot_id'] = '3rd to be updated - Cycle 2 - 1st Match Set'
        base_state_details['city'] = '1st Match - Cycle 2 - City 3'
        tls_23 = self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        base_state_details['jurisdiction_tax_lot_id'] = 'Single Unmatched - 2'
        base_state_details['city'] = 'Unmatched City - Cycle 2'
        tls_24 = self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        # Import file and create -Views and canonical records.
        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        match_buildings(self.import_file_2.id)

        # Cycle 3 / ImportFile 3
        base_state_details['import_file_id'] = self.import_file_3.id
        base_state_details['jurisdiction_tax_lot_id'] = 'To be updated - Cycle 3 - 1st Match Set'
        base_state_details['city'] = '1st Match - Cycle 3 - City 1'
        tls_31 = self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        base_state_details['jurisdiction_tax_lot_id'] = 'Single Unmatched - 3'
        base_state_details['city'] = 'Unmatched City - Cycle 3'
        tls_32 = self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        # Import file and create -Views and canonical records.
        self.import_file_3.mapping_done = True
        self.import_file_3.save()
        match_buildings(self.import_file_3.id)

        # Verify no matches or links
        self.assertEqual(9, TaxLotView.objects.count())
        self.assertEqual(9, TaxLotState.objects.count())
        self.assertEqual(9, TaxLot.objects.count())

        # At the moment, no two -Views have the same canonical records
        views_with_same_canonical_records = TaxLotView.objects.\
            values('taxlot_id').\
            annotate(times_used=Count('id')).\
            filter(times_used__gt=1)
        self.assertFalse(views_with_same_canonical_records.exists())

        # (Unrealistically) Make some match
        to_be_matched_ids = [
            tls_12.id,  # Cycle 1
            tls_21.id, tls_22.id, tls_23.id,  # Cycle 2
            tls_31.id,  # Cycle 3
        ]
        TaxLotState.objects.filter(id__in=to_be_matched_ids).update(jurisdiction_tax_lot_id='1st Match Set')

        # run match_merge_link on Sets that WON'T trigger merges or linkings
        match_merge_link(TaxLotView.objects.get(state_id=tls_13.id).id, 'TaxLotState')
        match_merge_link(TaxLotView.objects.get(state_id=tls_24.id).id, 'TaxLotState')
        match_merge_link(TaxLotView.objects.get(state_id=tls_32.id).id, 'TaxLotState')
        self.assertEqual(9, TaxLotView.objects.count())
        self.assertEqual(9, TaxLotState.objects.count())
        self.assertEqual(9, TaxLot.objects.count())

        # run match_merge_link on a Set that WILL trigger merges and linkings
        target_view = TaxLotView.objects.get(state_id=tls_11.id)
        merge_count, link_count, _view_id = match_merge_link(target_view.id, 'TaxLotState')

        self.assertEqual(5, merge_count)
        self.assertEqual(2, link_count)

        # Check merges by Cycle - use cities to check merge precedence order
        # Cycle 1
        cycle_1_views = TaxLotView.objects.filter(cycle_id=self.cycle_1.id)
        self.assertEqual(2, cycle_1_views.count())

        cycle_1_cities = list(cycle_1_views.prefetch_related('state').values_list('state__city', flat=True))
        expected_cities_1 = [
            '1st Match - Cycle 1 - City 1',  # tls_11 took precedence over tls_12, since tls_11's -View took precedence
            'Unmatched City - Cycle 1'
        ]
        self.assertCountEqual(expected_cities_1, cycle_1_cities)

        # Cycle 2
        cycle_2_views = TaxLotView.objects.filter(cycle_id=self.cycle_2.id)
        self.assertEqual(2, cycle_2_views.count())

        cycle_2_cities = list(cycle_2_views.prefetch_related('state').values_list('state__city', flat=True))
        expected_cities_2 = [
            '1st Match - Cycle 2 - City 3',  # tls_23 took precedence
            'Unmatched City - Cycle 2'
        ]
        self.assertCountEqual(expected_cities_2, cycle_2_cities)

        # Cycle 3 - No merges
        cycle_3_views = TaxLotView.objects.filter(cycle_id=self.cycle_3.id)
        self.assertEqual(2, cycle_3_views.count())

        # Check links
        views_by_canonical_record = TaxLotView.objects.\
            values('taxlot_id').\
            annotate(view_ids=ArrayAgg('id'), times_used=Count('id'))
        self.assertTrue(views_by_canonical_record.filter(times_used__gt=1).exists())

        # For linked views, the corresponding -States should match
        # In this case, all should have the same jurisdiction_tax_lot_id.
        for view_ids in views_by_canonical_record.values_list('view_ids', flat=True):
            base_state = TaxLotView.objects.get(id=view_ids[0]).state
            matching_view_ids = list(
                TaxLotView.objects.
                prefetch_related('state').
                filter(state__jurisdiction_tax_lot_id=base_state.jurisdiction_tax_lot_id).
                values_list('id', flat=True)
            )
            self.assertCountEqual(view_ids, matching_view_ids)

    def test_match_merge_link_for_properties_resuses_canonical_records_when_possible(self):
        """
        3 Cycles - 1 Property Set in each - all 3 will match after import
        2 Sets will be linked first. The last will be linked afterwards and will
        inherit the canonical record to establish the link with the other 2 Sets.
        """
        # Cycle 1 / ImportFile 1
        base_property_details = {
            'pm_property_id': 'To be update - Cycle 1',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        ps_11 = self.property_state_factory.get_property_state(**base_property_details)

        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Cycle 2 / ImportFile 2
        base_property_details['import_file_id'] = self.import_file_2.id
        base_property_details['pm_property_id'] = 'To be updated - Cycle 2'
        ps_21 = self.property_state_factory.get_property_state(**base_property_details)

        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        match_buildings(self.import_file_2.id)

        # Cycle 3 / ImportFile 3
        base_property_details['import_file_id'] = self.import_file_3.id
        base_property_details['pm_property_id'] = 'To be updated - Cycle 3'
        ps_31 = self.property_state_factory.get_property_state(**base_property_details)

        self.import_file_3.mapping_done = True
        self.import_file_3.save()
        match_buildings(self.import_file_3.id)

        self.assertEqual(3, PropertyView.objects.count())
        self.assertEqual(3, PropertyState.objects.count())
        self.assertEqual(3, Property.objects.count())

        # Update Sets 2 and 3 to match
        PropertyState.objects.filter(id__in=[ps_21.id, ps_31.id]).update(pm_property_id='Match Set')
        # Third Set's canonical record/ID should be linking ID.
        linking_id = PropertyView.objects.get(state_id=ps_31.id).property_id
        view_21 = PropertyView.objects.get(state_id=ps_21.id)

        match_merge_link(view_21.id, 'PropertyState')

        self.assertEqual(2, PropertyView.objects.filter(property_id=linking_id).count())
        self.assertEqual(linking_id, PropertyView.objects.get(state_id=ps_21.id).property_id)
        self.assertEqual(linking_id, PropertyView.objects.get(state_id=ps_31.id).property_id)

        # Update Set 1 to match
        PropertyState.objects.filter(id__in=[ps_11.id]).update(pm_property_id='Match Set')

        view_11 = PropertyView.objects.get(state_id=ps_11.id)
        match_merge_link(view_11.id, 'PropertyState')

        # All 3 sets should be linked using the first linking ID
        self.assertEqual(3, PropertyView.objects.count())
        self.assertEqual(3, PropertyView.objects.filter(property_id=linking_id).count())

    def test_match_merge_link_for_taxlots_resuses_canonical_records_when_possible(self):
        """
        3 Cycles - 1 TaxLot Set in each - all 3 will match after import
        2 Sets will be linked first. The last will be linked afterwards and will
        inherit the canonical record to establish the link with the other 2 Sets.
        """
        # Cycle 1 / ImportFile 1
        base_state_details = {
            'jurisdiction_tax_lot_id': 'To be update - Cycle 1',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        tls_11 = self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Cycle 2 / ImportFile 2
        base_state_details['import_file_id'] = self.import_file_2.id
        base_state_details['jurisdiction_tax_lot_id'] = 'To be updated - Cycle 2'
        tls_21 = self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        match_buildings(self.import_file_2.id)

        # Cycle 3 / ImportFile 3
        base_state_details['import_file_id'] = self.import_file_3.id
        base_state_details['jurisdiction_tax_lot_id'] = 'To be updated - Cycle 3'
        tls_31 = self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        self.import_file_3.mapping_done = True
        self.import_file_3.save()
        match_buildings(self.import_file_3.id)

        self.assertEqual(3, TaxLotView.objects.count())
        self.assertEqual(3, TaxLotState.objects.count())
        self.assertEqual(3, TaxLot.objects.count())

        # Update Sets 2 and 3 to match
        TaxLotState.objects.filter(id__in=[tls_21.id, tls_31.id]).update(jurisdiction_tax_lot_id='Match Set')
        # Third Set's canonical record/ID should be linking ID.
        linking_id = TaxLotView.objects.get(state_id=tls_31.id).taxlot_id
        view_21 = TaxLotView.objects.get(state_id=tls_21.id)

        match_merge_link(view_21.id, 'TaxLotState')

        self.assertEqual(2, TaxLotView.objects.filter(taxlot_id=linking_id).count())
        self.assertEqual(linking_id, TaxLotView.objects.get(state_id=tls_21.id).taxlot_id)
        self.assertEqual(linking_id, TaxLotView.objects.get(state_id=tls_31.id).taxlot_id)

        # Update Set 1 to match
        TaxLotState.objects.filter(id__in=[tls_11.id]).update(jurisdiction_tax_lot_id='Match Set')

        view_11 = TaxLotView.objects.get(state_id=tls_11.id)
        match_merge_link(view_11.id, 'TaxLotState')

        # All 3 sets should be linked using the first linking ID
        self.assertEqual(3, TaxLotView.objects.count())
        self.assertEqual(3, TaxLotView.objects.filter(taxlot_id=linking_id).count())

    def test_match_merge_link_for_properties_diassociated_records_if_no_longer_valid(self):
        """
        3 Cycles - 1 Property Set in each - all 3 are match linked after import.
        Make one not match anymore and rerun match merge link to unlink it.
        """
        # Cycle 1 / ImportFile 1
        base_property_details = {
            'pm_property_id': 'Match Set',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        ps_11 = self.property_state_factory.get_property_state(**base_property_details)

        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Cycle 2 / ImportFile 2
        base_property_details['import_file_id'] = self.import_file_2.id
        ps_21 = self.property_state_factory.get_property_state(**base_property_details)

        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        match_buildings(self.import_file_2.id)

        # Cycle 3 / ImportFile 3
        base_property_details['import_file_id'] = self.import_file_3.id
        ps_31 = self.property_state_factory.get_property_state(**base_property_details)

        self.import_file_3.mapping_done = True
        self.import_file_3.save()
        match_buildings(self.import_file_3.id)

        # Once updates are made to import process, these will correctly fail and be removed
        self.assertEqual(3, PropertyView.objects.count())
        self.assertEqual(3, PropertyState.objects.count())
        self.assertEqual(3, Property.objects.count())

        # Link all 3
        view_21 = PropertyView.objects.get(state_id=ps_21.id)
        match_merge_link(view_21.id, 'PropertyState')

        # Capture linked ID
        view_11 = PropertyView.objects.get(state_id=ps_11.id)
        initial_linked_id = view_11.property_id

        # Unlink the first
        PropertyState.objects.filter(id__in=[ps_11.id]).update(pm_property_id='No longer matches')
        match_merge_link(view_11.id, 'PropertyState')

        refreshed_view_11 = PropertyView.objects.get(state_id=ps_11.id)

        view_21 = PropertyView.objects.get(state_id=ps_21.id)
        view_31 = PropertyView.objects.get(state_id=ps_31.id)

        self.assertNotEqual(initial_linked_id, refreshed_view_11.property_id)
        self.assertEqual(initial_linked_id, view_21.property_id)
        self.assertEqual(initial_linked_id, view_31.property_id)

    def test_match_merge_link_for_taxlots_diassociated_records_if_no_longer_valid(self):
        """
        3 Cycles - 1 TaxLot Set in each - all 3 are match linked after import.
        Make one not match anymore and rerun match merge link to unlink it.
        """
        # Cycle 1 / ImportFile 1
        base_state_details = {
            'jurisdiction_tax_lot_id': 'Match Set',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        tls_11 = self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Cycle 2 / ImportFile 2
        base_state_details['import_file_id'] = self.import_file_2.id
        tls_21 = self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        match_buildings(self.import_file_2.id)

        # Cycle 3 / ImportFile 3
        base_state_details['import_file_id'] = self.import_file_3.id
        tls_31 = self.taxlot_state_factory.get_taxlot_state(**base_state_details)

        self.import_file_3.mapping_done = True
        self.import_file_3.save()
        match_buildings(self.import_file_3.id)

        # Once updates are made to import process, these will correctly fail and be removed
        self.assertEqual(3, TaxLotView.objects.count())
        self.assertEqual(3, TaxLotState.objects.count())
        self.assertEqual(3, TaxLot.objects.count())

        # Link all 3
        view_21 = TaxLotView.objects.get(state_id=tls_21.id)
        match_merge_link(view_21.id, 'TaxLotState')

        # Capture linked ID
        view_11 = TaxLotView.objects.get(state_id=tls_11.id)
        initial_linked_id = view_11.taxlot_id

        # Unlink the first
        TaxLotState.objects.filter(id__in=[tls_11.id]).update(jurisdiction_tax_lot_id='No longer matches')
        match_merge_link(view_11.id, 'TaxLotState')

        refreshed_view_11 = TaxLotView.objects.get(state_id=tls_11.id)

        view_21 = TaxLotView.objects.get(state_id=tls_21.id)
        view_31 = TaxLotView.objects.get(state_id=tls_31.id)

        self.assertNotEqual(initial_linked_id, refreshed_view_11.taxlot_id)
        self.assertEqual(initial_linked_id, view_21.taxlot_id)
        self.assertEqual(initial_linked_id, view_31.taxlot_id)

    def test_match_merge_link_for_properties_meters_persist_in_different_situations(self):
        """
        In the following order, check that meters persist in each scenario:
            - a new Property is used to link. Meters are merged in ID order with
            final priority given to target Property
            - unlinking happens. Meters are copied over.
            - an existing Property is used to link. Meters from the target
            Property are copied to the existing Property.
        """
        # Cycle 1 / ImportFile 1
        base_property_details = {
            'pm_property_id': 'To be update - Cycle 1',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        ps_11 = self.property_state_factory.get_property_state(**base_property_details)

        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Cycle 2 / ImportFile 2
        base_property_details['import_file_id'] = self.import_file_2.id
        base_property_details['pm_property_id'] = 'To be updated - Cycle 2'
        ps_21 = self.property_state_factory.get_property_state(**base_property_details)

        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        match_buildings(self.import_file_2.id)

        # Cycle 3 / ImportFile 3
        base_property_details['import_file_id'] = self.import_file_3.id
        base_property_details['pm_property_id'] = 'To be updated - Cycle 3'
        ps_31 = self.property_state_factory.get_property_state(**base_property_details)

        self.import_file_3.mapping_done = True
        self.import_file_3.save()
        match_buildings(self.import_file_3.id)

        self.assertEqual(3, PropertyView.objects.count())
        self.assertEqual(3, PropertyState.objects.count())
        self.assertEqual(3, Property.objects.count())

        """
        First case - The following is set up:
            - 3 overlapping readings are created between 3 Sets
            - 2 overlapping readings are created between the last 2 Sets
            - The 1st Set is targetted in the match_merge_link method

        Outcome:
            - The 3 overlapping readings should have the 1st Set's reading
            - The 2 overlapping readings should have the 3rd Set's reading
        """
        # Apply the same meter and an overlapping meter reading to each Property
        tz_obj = timezone(TIME_ZONE)
        for i, property in enumerate(Property.objects.all()):
            meter = Meter.objects.create(
                property=property,
                source=Meter.PORTFOLIO_MANAGER,
                source_id="same source ID",
                type=Meter.ELECTRICITY_GRID,
            )
            MeterReading.objects.create(
                meter=meter,
                start_time=make_aware(datetime(2018, 1, 1, 0, 0, 0), timezone=tz_obj),
                end_time=make_aware(datetime(2018, 1, 2, 0, 0, 0), timezone=tz_obj),
                reading=(i + 1) * 100,
                source_unit='kBtu (thousand Btu)',
                conversion_factor=1.00
            )

        # Create overlapping readings for meters associated to 2nd and 3rd Set
        meter_21 = Meter.objects.get(property_id=PropertyView.objects.get(state_id=ps_21.id).property_id)
        meter_31 = Meter.objects.get(property_id=PropertyView.objects.get(state_id=ps_31.id).property_id)
        MeterReading.objects.create(
            meter=meter_21,
            start_time=make_aware(datetime(2018, 2, 1, 0, 0, 0), timezone=tz_obj),
            end_time=make_aware(datetime(2018, 2, 2, 0, 0, 0), timezone=tz_obj),
            reading=212121,
            source_unit='kBtu (thousand Btu)',
            conversion_factor=1.00
        )
        MeterReading.objects.create(
            meter=meter_31,
            start_time=make_aware(datetime(2018, 2, 1, 0, 0, 0), timezone=tz_obj),
            end_time=make_aware(datetime(2018, 2, 2, 0, 0, 0), timezone=tz_obj),
            reading=313131,
            source_unit='kBtu (thousand Btu)',
            conversion_factor=1.00
        )

        # Update all Sets to match and run match merge link
        PropertyState.objects.update(pm_property_id='Match Set')
        view_11 = PropertyView.objects.get(state_id=ps_11.id)
        match_merge_link(view_11.id, 'PropertyState')

        # Check Meters and MeterReadings
        linking_property = PropertyView.objects.first().property
        self.assertEqual(1, linking_property.meters.count())
        agg_meter = linking_property.meters.first()
        self.assertEqual(2, agg_meter.meter_readings.count())

        self.assertTrue(agg_meter.meter_readings.filter(reading=100).exists())
        self.assertTrue(agg_meter.meter_readings.filter(reading=313131).exists())

        """
        Second Case - The following is set up:
            - 3 Sets linked with 2 readings shared amongst them.
            - Make 1st Set no longer match
            - Run match_merge_link method on 1st Set
        Outcome:
            - The 2 readings were copied over to the 1st Set's Property
        """
        PropertyState.objects.filter(id=ps_11.id).update(pm_property_id='No longer matches')
        view_11 = PropertyView.objects.get(state_id=ps_11.id)
        match_merge_link(view_11.id, 'PropertyState')

        # Check meter was copied
        view_11_unlinked_property = PropertyView.objects.get(state_id=ps_11.id).property

        self.assertEqual(1, view_11_unlinked_property.meters.count())

        copied_meter = view_11_unlinked_property.meters.first()
        self.assertNotEqual(agg_meter.id, copied_meter.id)
        self.assertEqual(2, copied_meter.meter_readings.count())

        """
        Third Case - The following is set up:
            - Create a new, unique reading for the newly created/copied Meter
            - Make 1st Set match again
            - Run match_merge_link method on 1st Set
        Outcome:
            - The newly created reading was copied over to the existing linking Property
        """
        MeterReading.objects.create(
            meter=copied_meter,
            start_time=make_aware(datetime(2018, 3, 1, 0, 0, 0), timezone=tz_obj),
            end_time=make_aware(datetime(2018, 3, 2, 0, 0, 0), timezone=tz_obj),
            reading=321,
            source_unit='kBtu (thousand Btu)',
            conversion_factor=1.00
        )

        PropertyState.objects.filter(id=ps_11.id).update(pm_property_id='Match Set')
        view_11 = PropertyView.objects.get(state_id=ps_11.id)
        match_merge_link(view_11.id, 'PropertyState')

        # Check MeterReadings - latest created reading was copied over
        self.assertEqual(3, agg_meter.meter_readings.count())
        self.assertTrue(agg_meter.meter_readings.filter(reading=100).exists())
        self.assertTrue(agg_meter.meter_readings.filter(reading=321).exists())
        self.assertTrue(agg_meter.meter_readings.filter(reading=313131).exists())


class TestMatchingExistingViewFullOrgMatchingProperties(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file_1, self.import_record_1, self.cycle_1 = selfvars

        cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.cycle_2 = cycle_factory.get_cycle(name="Cycle 2")
        self.import_record_2, self.import_file_2 = self.create_import_file(
            self.user, self.org, self.cycle_2
        )

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)

        """
        The set up for these tests include multiple Property sets
        across multiple Cycles. In this context, a "set" includes a -State,
        -View, and canonical record.

        Cycle 1 - 6 property sets total will be created.
        For each:
            - 2 sets match each other
            - 2 other sets match each other
            - 1 set doesn't match
            - 1 set doesn't match but links
        Cycle 2 - 6 property sets total will be created.
        For each:
            - 3 sets match
            - 2 sets w/ null fields (won't merge or link)
            - 1 set doesn't match but links
        """
        # Cycle 1 / ImportFile 1
        base_property_details = {
            'pm_property_id': '1st Match Set',
            'city': 'City 1',
            'property_name': '1st Match Set',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create 6 initially non-matching properties in first Cycle
        self.ps_11 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['pm_property_id'] = 'To be updated - 1st Match Set'
        base_property_details['property_name'] = '1st Match Set'
        base_property_details['city'] = 'City 2'
        self.ps_12 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['pm_property_id'] = '2nd Match Set'
        base_property_details['property_name'] = '2nd Match Set'
        base_property_details['city'] = 'City 3'
        self.ps_13 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['pm_property_id'] = 'To be updated - 2nd Match Set'
        base_property_details['property_name'] = '2nd Match Set'
        base_property_details['city'] = 'City 4'
        self.ps_14 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['pm_property_id'] = 'Single Unmatched'
        base_property_details['property_name'] = 'Single Unmatched'
        base_property_details['city'] = 'City 5'
        self.ps_15 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['pm_property_id'] = 'Single to be Linked!'
        base_property_details['property_name'] = 'Single to be Linked!'
        base_property_details['city'] = 'City 6'
        self.ps_16 = self.property_state_factory.get_property_state(**base_property_details)

        # Import file and create -Views and canonical records.
        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Cycle 2 / ImportFile 2
        base_property_details = {
            'pm_property_id': '1st Match Set - 2',
            'city': 'City 1',
            'property_name': '1st Match Set',
            'import_file_id': self.import_file_2.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create 6 initially non-matching properties in second Cycle
        self.ps_21 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['pm_property_id'] = 'To be updated 1 - 1st Match Set - 2'
        base_property_details['property_name'] = '1st Match Set'
        base_property_details['city'] = 'City 2'
        self.ps_22 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['pm_property_id'] = 'To be updated 2 - 1st Match Set - 2'
        base_property_details['property_name'] = '1st Match Set'
        base_property_details['city'] = 'City 3'
        self.ps_23 = self.property_state_factory.get_property_state(**base_property_details)

        del base_property_details['pm_property_id']
        del base_property_details['property_name']
        base_property_details['city'] = 'Null Fields 1'
        self.ps_24 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['city'] = 'Null Fields 2'
        self.ps_25 = self.property_state_factory.get_property_state(**base_property_details)

        base_property_details['pm_property_id'] = 'Single to be Linked! - will be updated later - 2'
        base_property_details['property_name'] = 'Single to be Linked!'
        base_property_details['city'] = 'City 6'
        self.ps_26 = self.property_state_factory.get_property_state(**base_property_details)

        # Import file and create -Views and canonical records.
        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        match_buildings(self.import_file_2.id)

    def test_properties_whole_org_match_merge_link_preview(self):
        # save all the columns in the state to the database so we can setup column list settings
        Column.save_column_names(self.ps_11)
        # get the columnlistsetting (default) for all columns
        column_list_factory = FakeColumnListSettingsFactory(organization=self.org)
        columnlistsetting = column_list_factory.get_columnlistsettings(columns=['property_name', 'city'])

        # Check all property sets were created without match merges
        self.assertEqual(12, Property.objects.count())
        self.assertEqual(12, PropertyState.objects.count())
        self.assertEqual(12, PropertyView.objects.count())

        summary = whole_org_match_merge_link(self.org.id, 'PropertyState', ['property_name'])

        property_name_key = 'property_name_' + str(columnlistsetting.columns.get(column_name='property_name').id)
        city_key = 'city_' + str(columnlistsetting.columns.get(column_name='city').id)

        # Check all property sets were created without match merges
        self.assertEqual(12, Property.objects.count())
        self.assertEqual(12, PropertyState.objects.count())
        self.assertEqual(12, PropertyView.objects.count())

        result_1 = summary[self.cycle_1.id]
        self.assertEqual(len(result_1), 4)
        property_name_or_city_ids_1 = {
            (ps.get(property_name_key) or ps[city_key]): ps['id']
            for ps
            in result_1
        }

        result_2 = summary[self.cycle_2.id]
        self.assertEqual(len(result_2), 4)
        property_name_or_city_ids_2 = {
            (ps.get(property_name_key) or ps[city_key]): ps['id']
            for ps
            in result_2
        }

        # check links
        self.assertEqual(property_name_or_city_ids_1['Single to be Linked!'], property_name_or_city_ids_2['Single to be Linked!'])
        self.assertEqual(property_name_or_city_ids_1['1st Match Set'], property_name_or_city_ids_2['1st Match Set'])

        # check not linked from each Cycle
        self.assertFalse(property_name_or_city_ids_1['Single Unmatched'] in property_name_or_city_ids_2.values())
        self.assertFalse(property_name_or_city_ids_1['2nd Match Set'] in property_name_or_city_ids_2.values())

        self.assertFalse(property_name_or_city_ids_2['Null Fields 1'] in property_name_or_city_ids_1.values())
        self.assertFalse(property_name_or_city_ids_2['Null Fields 2'] in property_name_or_city_ids_1.values())

    def test_properties_whole_org_match_merge_link(self):
        # Make some match but don't trigger matching round
        PropertyState.objects.filter(pk=self.ps_12.id).update(pm_property_id='1st Match Set')
        PropertyState.objects.filter(pk=self.ps_14.id).update(pm_property_id='2nd Match Set')
        PropertyState.objects.filter(pk__in=[self.ps_21.id, self.ps_23.id]).update(pm_property_id='1st Match Set')
        PropertyState.objects.filter(pk=self.ps_26.id).update(pm_property_id='Single to be Linked!')

        # Give merge priority to -States with City 2
        prioritized_property = PropertyState.objects.get(id=self.ps_22.id)
        prioritized_property.pm_property_id = '1st Match Set'
        prioritized_property.save()

        # Check all property sets were created without match merges
        self.assertEqual(12, Property.objects.count())
        self.assertEqual(12, PropertyState.objects.count())
        self.assertEqual(12, PropertyView.objects.count())

        # Capture initial canonical IDs of impending matches - used for tests
        initial_property_ids_of_matches = list(
            PropertyView.objects.
            select_related('state').
            filter(state__pm_property_id__in=['1st Match Set', '2nd Match Set', 'Single to be Linked!']).
            values_list('property_id', flat=True)
        )

        summary = whole_org_match_merge_link(self.org.id, 'PropertyState')

        """
        Check the state of the property records.

        The matching field being looked at is pm_property_id.

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

        # Check canonical record counts
        # 6 = 12 - 2 [merged in Cycle 1] - 2 [merged in Cycle 2] - 2 [deleted and unused since link was created]
        self.assertEqual(6, Property.objects.count())

        # Check that previous canonical records that were merged and/or linked are no longer used
        self.assertFalse(Property.objects.filter(pk__in=initial_property_ids_of_matches).exists())

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

        # Check -State counts
        # 16 = 12 + 2 [Cycle 1 merges] + 2 [Cycle 2 merges]
        self.assertEqual(16, PropertyState.objects.count())

        # Check -States part of merges are no longer associated to -Views
        merged_ps_ids = [
            self.ps_11.id, self.ps_12.id,  # Cycle 1
            self.ps_13.id, self.ps_14.id,  # Cycle 1
            self.ps_21.id, self.ps_22.id, self.ps_23.id  # Cycle 2
        ]
        self.assertFalse(PropertyView.objects.filter(state_id__in=merged_ps_ids).exists())

        # Check -States NOT part of merges are still associated to -Views
        self.assertTrue(PropertyView.objects.filter(state_id=self.ps_15.id).exists())
        self.assertTrue(PropertyView.objects.filter(state_id=self.ps_16.id).exists())

        self.assertTrue(PropertyView.objects.filter(state_id=self.ps_24.id).exists())
        self.assertTrue(PropertyView.objects.filter(state_id=self.ps_25.id).exists())
        self.assertTrue(PropertyView.objects.filter(state_id=self.ps_26.id).exists())

        """
        Check Merges occurred correctly, with priority given to most recently
        updated or, in this case, newer -States as evidenced by 'city' values
        Each Cycle should have 4 PropertyStates with unique cities in each Cycle.
        """
        cycle_1_pviews = PropertyView.objects.filter(cycle_id=self.cycle_1.id)
        cycle_1_pstates = PropertyState.objects.filter(pk__in=Subquery(cycle_1_pviews.values('state_id')))

        self.assertEqual(4, cycle_1_pstates.count())
        self.assertEqual(1, cycle_1_pstates.filter(city='City 2').count())
        self.assertEqual(1, cycle_1_pstates.filter(city='City 4').count())
        self.assertEqual(1, cycle_1_pstates.filter(city='City 5').count())
        self.assertEqual(1, cycle_1_pstates.filter(city='City 6').count())

        cycle_2_pviews = PropertyView.objects.filter(cycle_id=self.cycle_2.id)
        cycle_2_pstates = PropertyState.objects.filter(pk__in=Subquery(cycle_2_pviews.values('state_id')))

        self.assertEqual(4, cycle_2_pstates.count())
        # Note: merge priority was explicitly given to -State with City 2
        self.assertEqual(1, cycle_2_pstates.filter(city='City 2').count())
        self.assertEqual(1, cycle_2_pstates.filter(city='Null Fields 1').count())
        self.assertEqual(1, cycle_2_pstates.filter(city='Null Fields 2').count())
        self.assertEqual(1, cycle_2_pstates.filter(city='City 6').count())

        # Finally, check method returned expected summary
        expected_summary = {
            'PropertyState': {
                'merged_count': 7,
                'linked_sets_count': 2,
            },
        }

        self.assertEqual(
            summary['PropertyState']['merged_count'],
            expected_summary['PropertyState']['merged_count']
        )
        self.assertEqual(
            summary['PropertyState']['linked_sets_count'],
            expected_summary['PropertyState']['linked_sets_count']
        )


class TestMatchingExistingViewFullOrgMatchingTaxLots(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file_1, self.import_record_1, self.cycle_1 = selfvars

        cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.cycle_2 = cycle_factory.get_cycle(name="Cycle 2")
        self.import_record_2, self.import_file_2 = self.create_import_file(
            self.user, self.org, self.cycle_2
        )

        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

        """
        The set up for these tests include multiple TaxLot sets
        across multiple Cycles. In this context, a "set" includes a -State,
        -View, and canonical record.

        Cycle 1 - 6 taxlot sets total will be created.
        For each:
            - 2 sets match each other
            - 2 other sets match each other
            - 1 set doesn't match
            - 1 set doesn't match but links
        Cycle 2 - 6 taxlot sets total will be created.
        For each:
            - 3 sets match
            - 2 sets w/ null fields (won't merge or link)
            - 1 set doesn't match but links
        """
        # Cycle 1 / ImportFile 1
        base_taxlot_details = {
            'jurisdiction_tax_lot_id': '1st Match Set',
            'city': 'City 1',
            'district': '1st Match Set',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create 6 initially non-matching taxlots in first Cycle
        self.tls_11 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        base_taxlot_details['jurisdiction_tax_lot_id'] = 'To be updated - 1st Match Set'
        base_taxlot_details['district'] = '1st Match Set'
        base_taxlot_details['city'] = 'City 2'
        self.tls_12 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        base_taxlot_details['jurisdiction_tax_lot_id'] = '2nd Match Set'
        base_taxlot_details['district'] = '2nd Match Set'
        base_taxlot_details['city'] = 'City 3'
        self.tls_13 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        base_taxlot_details['jurisdiction_tax_lot_id'] = 'To be updated - 2nd Match Set'
        base_taxlot_details['district'] = '2nd Match Set'
        base_taxlot_details['city'] = 'City 4'
        self.tls_14 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        base_taxlot_details['jurisdiction_tax_lot_id'] = 'Single Unmatched'
        base_taxlot_details['district'] = 'Single Unmatched'
        base_taxlot_details['city'] = 'City 5'
        self.tls_15 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        base_taxlot_details['jurisdiction_tax_lot_id'] = 'Single to be Linked!'
        base_taxlot_details['district'] = 'Single to be Linked!'
        base_taxlot_details['city'] = 'City 6'
        self.tls_16 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        # Import file and create -Views and canonical records.
        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Check all property and taxlot sets were created without match merges
        self.assertEqual(6, TaxLot.objects.count())
        self.assertEqual(6, TaxLotState.objects.count())
        self.assertEqual(6, TaxLotView.objects.count())

        # Cycle 2 / ImportFile 2
        base_taxlot_details = {
            'jurisdiction_tax_lot_id': '1st Match Set - 2',
            'city': 'City 1',
            'district': '1st Match Set',
            'import_file_id': self.import_file_2.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create 6 initially non-matching taxlots in second Cycle
        self.tls_21 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        base_taxlot_details['jurisdiction_tax_lot_id'] = 'To be updated 1 - 1st Match Set - 2'
        base_taxlot_details['district'] = '1st Match Set'
        base_taxlot_details['city'] = 'City 2'
        self.tls_22 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        base_taxlot_details['jurisdiction_tax_lot_id'] = 'To be updated 2 - 1st Match Set - 2'
        base_taxlot_details['district'] = '1st Match Set'
        base_taxlot_details['city'] = 'City 3'
        self.tls_23 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        del base_taxlot_details['jurisdiction_tax_lot_id']
        del base_taxlot_details['district']
        base_taxlot_details['city'] = 'Null Fields 1'
        self.tls_24 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        base_taxlot_details['city'] = 'Null Fields 2'
        self.tls_25 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        base_taxlot_details['jurisdiction_tax_lot_id'] = 'Single to be Linked! - will be updated later - 2'
        base_taxlot_details['district'] = 'Single to be Linked!'
        base_taxlot_details['city'] = 'City 6'
        self.tls_26 = self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        # Import file and create -Views and canonical records.
        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        match_buildings(self.import_file_2.id)

    def test_taxlots_whole_org_match_merge_link_preview(self):
        # save all the columns in the state to the database so we can setup column list settings
        Column.save_column_names(self.tls_11)
        # get the columnlistsetting (default) for all columns
        column_list_factory = FakeColumnListSettingsFactory(organization=self.org)
        columnlistsetting = column_list_factory.get_columnlistsettings(
            inventory_type=VIEW_LIST_TAXLOT,
            columns=['district', 'city'],
            table_name='TaxLotState'
        )

        # Check all property sets were created without match merges
        self.assertEqual(12, TaxLot.objects.count())
        self.assertEqual(12, TaxLotState.objects.count())
        self.assertEqual(12, TaxLotView.objects.count())

        summary = whole_org_match_merge_link(self.org.id, 'TaxLotState', ['district'])

        district_key = 'district_' + str(columnlistsetting.columns.get(column_name='district').id)
        city_key = 'city_' + str(columnlistsetting.columns.get(column_name='city').id)

        # Check all property sets were created without match merges
        self.assertEqual(12, TaxLot.objects.count())
        self.assertEqual(12, TaxLotState.objects.count())
        self.assertEqual(12, TaxLotView.objects.count())

        result_1 = summary[self.cycle_1.id]
        self.assertEqual(len(result_1), 4)
        district_or_city_ids_1 = {
            (tls.get(district_key) or tls[city_key]): tls['id']
            for tls
            in result_1
        }

        result_2 = summary[self.cycle_2.id]
        self.assertEqual(len(result_2), 4)
        district_or_city_ids_2 = {
            (tls.get(district_key) or tls[city_key]): tls['id']
            for tls
            in result_2
        }

        # check links
        self.assertEqual(district_or_city_ids_1['Single to be Linked!'], district_or_city_ids_2['Single to be Linked!'])
        self.assertEqual(district_or_city_ids_1['1st Match Set'], district_or_city_ids_2['1st Match Set'])

        # check not linked from each Cycle
        self.assertFalse(district_or_city_ids_1['Single Unmatched'] in district_or_city_ids_2.values())
        self.assertFalse(district_or_city_ids_1['2nd Match Set'] in district_or_city_ids_2.values())

        self.assertFalse(district_or_city_ids_2['Null Fields 1'] in district_or_city_ids_1.values())
        self.assertFalse(district_or_city_ids_2['Null Fields 2'] in district_or_city_ids_1.values())

    def test_whole_org_match_merge_link_taxlots(self):
        # Make some match but don't trigger matching round
        TaxLotState.objects.filter(pk=self.tls_12.id).update(jurisdiction_tax_lot_id='1st Match Set')
        TaxLotState.objects.filter(pk=self.tls_14.id).update(jurisdiction_tax_lot_id='2nd Match Set')
        TaxLotState.objects.filter(pk__in=[self.tls_21.id, self.tls_23.id]).update(jurisdiction_tax_lot_id='1st Match Set')
        TaxLotState.objects.filter(pk=self.tls_26.id).update(jurisdiction_tax_lot_id='Single to be Linked!')

        # Give merge priority to -States with City 2
        prioritized_taxlot = TaxLotState.objects.get(id=self.tls_22.id)
        prioritized_taxlot.jurisdiction_tax_lot_id = '1st Match Set'
        prioritized_taxlot.save()

        # Check all taxlot sets were created without match merges
        self.assertEqual(12, TaxLot.objects.count())
        self.assertEqual(12, TaxLotState.objects.count())
        self.assertEqual(12, TaxLotView.objects.count())

        # Capture initial canonical IDs of impending matches - used for tests
        initial_taxlot_ids_of_matches = list(
            TaxLotView.objects.
            select_related('state').
            filter(state__jurisdiction_tax_lot_id__in=['1st Match Set', '2nd Match Set', 'Single to be Linked!']).
            values_list('taxlot_id', flat=True)
        )

        summary = whole_org_match_merge_link(self.org.id, 'TaxLotState')

        """
        Now that the set up is complete, test the state of taxlot records.

        The matching field being looked at is jurisdiction_tax_lot_id.

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
        self.assertEqual(8, TaxLotView.objects.count())

        # Check canonical record counts
        # 6 = 12 - 2 [merged in Cycle 1] - 2 [merged in Cycle 2] - 2 [deleted and unused since link was created]
        self.assertEqual(6, TaxLot.objects.count())

        # Check that previous canonical records that were merged and/or linked are no longer used
        self.assertFalse(TaxLot.objects.filter(pk__in=initial_taxlot_ids_of_matches).exists())

        # Check that a link was created for -States across Cycles
        # Specifically, canonical IDs should match but cycles should be different
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

        # Check -States part of merges are no longer associated to -Views
        merged_tls_ids = [
            self.tls_11.id, self.tls_12.id,  # Cycle 1
            self.tls_13.id, self.tls_14.id,  # Cycle 1
            self.tls_21.id, self.tls_22.id, self.tls_23.id  # Cycle 2
        ]
        self.assertFalse(TaxLotView.objects.filter(state_id__in=merged_tls_ids).exists())

        # Check -States NOT part of merges are still associated to -Views
        self.assertTrue(TaxLotView.objects.filter(state_id=self.tls_15.id).exists())
        self.assertTrue(TaxLotView.objects.filter(state_id=self.tls_16.id).exists())

        self.assertTrue(TaxLotView.objects.filter(state_id=self.tls_24.id).exists())
        self.assertTrue(TaxLotView.objects.filter(state_id=self.tls_25.id).exists())
        self.assertTrue(TaxLotView.objects.filter(state_id=self.tls_26.id).exists())

        """
        Check Merges occurred correctly, with priority given to most recently
        updated or, in this case, newer -States as evidenced by 'city' values
        Each Cycle should have 4 TaxLotStates with unique cities in each Cycle.
        """
        cycle_1_tlviews = TaxLotView.objects.filter(cycle_id=self.cycle_1.id)
        cycle_1_tlstates = TaxLotState.objects.filter(pk__in=Subquery(cycle_1_tlviews.values('state_id')))

        self.assertEqual(4, cycle_1_tlstates.count())
        self.assertEqual(1, cycle_1_tlstates.filter(city='City 2').count())
        self.assertEqual(1, cycle_1_tlstates.filter(city='City 4').count())
        self.assertEqual(1, cycle_1_tlstates.filter(city='City 5').count())
        self.assertEqual(1, cycle_1_tlstates.filter(city='City 6').count())

        cycle_2_tlviews = TaxLotView.objects.filter(cycle_id=self.cycle_2.id)
        cycle_2_tlstates = TaxLotState.objects.filter(pk__in=Subquery(cycle_2_tlviews.values('state_id')))

        self.assertEqual(4, cycle_2_tlstates.count())
        # Note: merge priority was explicitly given to -State with City 2
        self.assertEqual(1, cycle_2_tlstates.filter(city='City 2').count())
        self.assertEqual(1, cycle_2_tlstates.filter(city='Null Fields 1').count())
        self.assertEqual(1, cycle_2_tlstates.filter(city='Null Fields 2').count())
        self.assertEqual(1, cycle_2_tlstates.filter(city='City 6').count())

        # Finally, check method returned expected summary
        expected_summary = {
            'TaxLotState': {
                'merged_count': 7,
                'linked_sets_count': 2,
            },
        }

        self.assertEqual(
            summary['TaxLotState']['merged_count'],
            expected_summary['TaxLotState']['merged_count']
        )
        self.assertEqual(
            summary['TaxLotState']['linked_sets_count'],
            expected_summary['TaxLotState']['linked_sets_count']
        )


class TestMatchingExistingViewFullOrgMatchingUnlinking(DataMappingBaseTestCase):
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

    def test_whole_org_match_merge_link_properties_unlink_if_applicable(self):
        # Cycle 1 / ImportFile 1
        base_property_details = {
            'pm_property_id': '1st Match Set',
            'city': 'City 1',
            'property_name': '123DifferentName',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create initially matching property in first Cycle
        self.property_state_factory.get_property_state(**base_property_details)

        # Import file and create -Views and canonical records.
        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Cycle 2 / ImportFile 2
        base_property_details = {
            'pm_property_id': '1st Match Set',
            'city': 'City 1',
            'property_name': '456DifferentName',
            'import_file_id': self.import_file_2.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create initially matching property in second Cycle
        self.property_state_factory.get_property_state(**base_property_details)

        # Import file and create -Views and canonical records.
        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        match_buildings(self.import_file_2.id)

        # Propose different `property_name` matching - populated
        summary_1 = whole_org_match_merge_link(self.org.id, 'PropertyState', ['property_name'])

        canonical_ids = [records[0]['id'] for records in summary_1.values() if records]

        self.assertNotEqual(canonical_ids[0], canonical_ids[1])

        # Propose different `owner_address` matching - not-populated
        summary_2 = whole_org_match_merge_link(self.org.id, 'PropertyState', ['owner_address'])

        canonical_ids = [records[0]['id'] for records in summary_2.values() if records]

        self.assertNotEqual(canonical_ids[0], canonical_ids[1])

    def test_whole_org_match_merge_link_taxlots_unlink_if_applicable(self):
        # Cycle 1 / ImportFile 1
        base_taxlot_details = {
            'jurisdiction_tax_lot_id': '1st Match Set',
            'city': 'City 1',
            'district': '123DifferentName',
            'import_file_id': self.import_file_1.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create initially matching property in first Cycle
        self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        # Import file and create -Views and canonical records.
        self.import_file_1.mapping_done = True
        self.import_file_1.save()
        match_buildings(self.import_file_1.id)

        # Cycle 2 / ImportFile 2
        base_taxlot_details = {
            'jurisdiction_tax_lot_id': '1st Match Set',
            'city': 'City 1',
            'district': '456DifferentName',
            'import_file_id': self.import_file_2.id,
            'data_state': DATA_STATE_MAPPING,
            'no_default_data': False,
        }
        # Create initially matching property in second Cycle
        self.taxlot_state_factory.get_taxlot_state(**base_taxlot_details)

        # Import file and create -Views and canonical records.
        self.import_file_2.mapping_done = True
        self.import_file_2.save()
        match_buildings(self.import_file_2.id)

        # Propose different `district` matching - populated
        summary_1 = whole_org_match_merge_link(self.org.id, 'TaxLotState', ['district'])

        canonical_ids = [records[0]['id'] for records in summary_1.values() if records]

        self.assertNotEqual(canonical_ids[0], canonical_ids[1])

        # Propose different `block_number` matching - not-populated
        summary_2 = whole_org_match_merge_link(self.org.id, 'TaxLotState', ['block_number'])

        canonical_ids = [records[0]['id'] for records in summary_2.values() if records]

        self.assertNotEqual(canonical_ids[0], canonical_ids[1])
