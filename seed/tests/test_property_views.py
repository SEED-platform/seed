# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json
from datetime import datetime

from django.core.urlresolvers import reverse
from django.utils import timezone

from seed.landing.models import SEEDUser as User
from seed.models import (
    PropertyState,
    PropertyView,
)
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakeColumnFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakeTaxLotStateFactory,
    FakePropertyViewFactory,
)
from seed.tests.util import DeleteModelsTestCase
from seed.utils.organizations import create_organization

COLUMNS_TO_SEND = [
    'project_id',
    'address_line_1',
    'city',
    'state_province',
    'postal_code',
    'pm_parent_property_id',
    'calculated_taxlot_ids',
    'primary',
    'extra_data_field',
    'jurisdiction_tax_lot_id'
]


class PropertyViewTests(DeleteModelsTestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        self.column_factory = FakeColumnFactory(organization=self.org)
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)
        self.cycle = self.cycle_factory.get_cycle(
            start=datetime(2010, 10, 10, tzinfo=timezone.get_current_timezone()))
        self.client.login(**user_details)

    def test_get_and_edit_properties(self):
        state = self.property_state_factory.get_property_state()
        prprty = self.property_factory.get_property()
        view = PropertyView.objects.create(
            property=prprty, cycle=self.cycle, state=state
        )
        params = {
            'organization_id': self.org.pk,
            'page': 1,
            'per_page': 999999999,
            'columns': COLUMNS_TO_SEND,
        }

        url = reverse('api:v2:properties-list') + '?cycle_id={}'.format(self.cycle.pk)
        response = self.client.get(url, params)
        result = json.loads(response.content)
        results = result['results'][0]
        self.assertEqual(len(result['results']), 1)
        self.assertEqual(results['address_line_1'], state.address_line_1)

        db_created_time = results['created']
        db_updated_time = results['updated']
        self.assertTrue(db_created_time is not None)
        self.assertTrue(db_updated_time is not None)

        # update the address
        new_data = {
            "state": {
                "address_line_1": "742 Evergreen Terrace"
            }
        }
        url = reverse('api:v2:properties-detail', args=[view.id]) + '?organization_id={}'.format(self.org.pk)
        response = self.client.put(url, json.dumps(new_data), content_type='application/json')
        result = json.loads(response.content)
        self.assertEqual(result['status'], 'success')

        # the above call returns data from the PropertyState, need to get the Property --
        # call the get on the same API to retrieve it
        response = self.client.get(url, content_type='application/json')
        result = json.loads(response.content)
        # make sure the address was updated and that the datetimes were modified
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['state']['address_line_1'], '742 Evergreen Terrace')
        self.assertEqual(datetime.strptime(db_created_time, "%Y-%m-%dT%H:%M:%S.%fZ").replace(microsecond=0),
                         datetime.strptime(result['property']['created'], "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                             microsecond=0))
        self.assertGreater(datetime.strptime(result['property']['updated'], "%Y-%m-%dT%H:%M:%S.%fZ"),
                           datetime.strptime(db_updated_time, "%Y-%m-%dT%H:%M:%S.%fZ"))

    def test_search_identifier(self):
        self.property_view_factory.get_property_view(cycle=self.cycle, custom_id_1='123456')
        self.property_view_factory.get_property_view(cycle=self.cycle, custom_id_1='987654 Long Street')
        self.property_view_factory.get_property_view(cycle=self.cycle, address_line_1='123 Main Street')
        self.property_view_factory.get_property_view(cycle=self.cycle, address_line_1='Hamilton Road',
                                                     analysis_state=PropertyState.ANALYSIS_STATE_QUEUED)
        self.property_view_factory.get_property_view(cycle=self.cycle, custom_id_1='long road',
                                                     analysis_state=PropertyState.ANALYSIS_STATE_QUEUED)

        # Typically looks like this
        # http://localhost:8000/api/v2.1/properties/?organization_id=265&cycle=219&identifier=09-IS

        # check for all items
        query_params = "?cycle={}&organization_id={}".format(self.cycle.pk, self.org.pk)
        url = reverse('api:v2.1:properties-list') + query_params
        response = self.client.get(url)
        result = json.loads(response.content)
        self.assertEqual(result['status'], 'success')
        results = result['properties']
        self.assertEqual(len(results), 5)

        # check for 2 items with 123
        query_params = "?cycle={}&organization_id={}&identifier={}".format(self.cycle.pk, self.org.pk, '123')
        url = reverse('api:v2.1:properties-list') + query_params
        response = self.client.get(url)
        result = json.loads(response.content)
        self.assertEqual(result['status'], 'success')
        results = result['properties']
        # print out the result of this when there are more than two in an attempt to catch the
        # non-deterministic part of this test
        if len(results) > 2:
            print results

        self.assertEqual(len(results), 2)

        # check the analysis states
        query_params = "?cycle={}&organization_id={}&analysis_state={}".format(self.cycle.pk, self.org.pk, 'Completed')
        url = reverse('api:v2.1:properties-list') + query_params
        response = self.client.get(url)
        result = json.loads(response.content)
        self.assertEqual(result['status'], 'success')
        results = result['properties']
        self.assertEqual(len(results), 0)

        query_params = "?cycle={}&organization_id={}&analysis_state={}".format(
            self.cycle.pk, self.org.pk, 'Not Started'
        )
        url = reverse('api:v2.1:properties-list') + query_params
        response = self.client.get(url)
        result = json.loads(response.content)
        self.assertEqual(result['status'], 'success')
        results = result['properties']
        self.assertEqual(len(results), 3)

        query_params = "?cycle={}&organization_id={}&analysis_state={}".format(
            self.cycle.pk, self.org.pk, 'Queued'
        )
        url = reverse('api:v2.1:properties-list') + query_params
        response = self.client.get(url)
        result = json.loads(response.content)
        self.assertEqual(result['status'], 'success')
        results = result['properties']
        self.assertEqual(len(results), 2)

        # check the combination of both the identifier and the analysis state
        query_params = "?cycle={}&organization_id={}&identifier={}&analysis_state={}".format(
            self.cycle.pk, self.org.pk, 'Long', 'Queued'
        )
        url = reverse('api:v2.1:properties-list') + query_params
        response = self.client.get(url)
        result = json.loads(response.content)
        self.assertEqual(result['status'], 'success')
        results = result['properties']
        self.assertEqual(len(results), 1)
