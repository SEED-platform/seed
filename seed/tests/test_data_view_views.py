# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
import json

from django.test import TestCase
from django.urls import reverse

from seed.models import Column, DataAggregation, DataView, User
from seed.test_helpers.fake import FakeCycleFactory
from seed.utils.organizations import create_organization


class DataViewViewTests(TestCase):
    """
    Test DataView model
    """

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'first_name': 'Johnny',
            'last_name': 'Energy',
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, _, _ = create_organization(self.user, "test-organization-a")
        self.client.login(**user_details)
        self.cycle1 = FakeCycleFactory(organization=self.org, user=self.user).get_cycle(name="Cycle A")
        self.cycle2 = FakeCycleFactory(organization=self.org, user=self.user).get_cycle(name="Cycle B")
        self.cycle3 = FakeCycleFactory(organization=self.org, user=self.user).get_cycle(name="Cycle C")
        self.cycle4 = FakeCycleFactory(organization=self.org, user=self.user).get_cycle(name="Cycle D")

        self.column1 = Column.objects.create(column_name='column 1', organization=self.org,)
        self.column2 = Column.objects.create(column_name='column 2', organization=self.org,)
        self.column3 = Column.objects.create(column_name='column 3', organization=self.org,)

        self.data_aggregation1 = DataAggregation.objects.create(
            name='column1 max',
            column=self.column1,
            type=2,
            organization=self.org
        )
        self.data_aggregation2 = DataAggregation.objects.create(
            name='column1 min',
            column=self.column1,
            type=3,
            organization=self.org
        )
        self.data_aggregation3 = DataAggregation.objects.create(
            name='column1 sum',
            column=self.column1,
            type=4,
            organization=self.org
        )

        self.data_view1 = DataView.objects.create(name='data view 1', filter_group=[1, 2, 3, 4], organization=self.org)
        self.data_view1.columns.set([self.column1, self.column2])
        self.data_view1.cycles.set([self.cycle1, self.cycle3, self.cycle4])
        self.data_view1.data_aggregations.set([self.data_aggregation2, self.data_aggregation3])

        self.data_view2 = DataView.objects.create(name='data view 2', filter_group=[5, 6, 7, 8], organization=self.org)
        self.data_view2.columns.set([self.column1, self.column2, self.column3])
        self.data_view2.cycles.set([self.cycle2, self.cycle4])
        self.data_view2.data_aggregations.set([self.data_aggregation1, self.data_aggregation2, self.data_aggregation3])

    def test_data_view_model(self):
        data_views = DataView.objects.all()
        self.assertEqual(2, len(data_views))

        data_view1 = data_views[0]
        self.assertEqual(2, len(data_view1.columns.all()))
        self.assertEqual(3, len(data_view1.cycles.all()))
        self.assertEqual(2, len(data_view1.data_aggregations.all()))
        self.assertEqual([1, 2, 3, 4], data_view1.filter_group)

        data_view2 = data_views[1]
        self.assertEqual(3, len(data_view2.columns.all()))
        self.assertEqual(2, len(data_view2.cycles.all()))
        self.assertEqual(3, len(data_view2.data_aggregations.all()))
        self.assertEqual([5, 6, 7, 8], data_view2.filter_group)

    def test_data_view_create_endpoint(self):
        self.assertEqual(2, len(DataView.objects.all()))

        response = self.client.get(
            reverse('api:v3:data_views-list') + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )

        self.assertEqual(2, len(json.loads(response.content)['message']))

        response = self.client.post(
            reverse('api:v3:data_views-list') + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                "name": "data_view3",
                "filter_group": [11, 12, 13, 14],
                "columns": [self.column1.id, self.column2.id, self.column3.id],
                "cycles": [self.cycle1.id, self.cycle2.id, self.cycle3.id],
                "data_aggregations": [self.data_aggregation1.id, self.data_aggregation2.id]

            }),
            content_type='application/json'
        )
        data = json.loads(response.content)
        self.assertEqual(data['data_view']['name'], 'data_view3')
        self.assertEqual(data['data_view']['organization'], self.org.id)
        self.assertTrue(bool(data['data_view']['id']))

        response = self.client.get(
            reverse('api:v3:data_views-list') + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )

        self.assertEqual(3, len(json.loads(response.content)['message']))

        data_view = DataView.objects.get(name='data_view3')
        response = self.client.delete(
            reverse('api:v3:data_views-detail', args=[data_view.id]) + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )

        response = self.client.get(
            reverse('api:v3:data_views-list') + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )

        self.assertEqual(2, len(json.loads(response.content)['message']))

    def test_data_view_create_bad_data(self):
        response = self.client.post(
            reverse('api:v3:data_views-list') + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                "name": "data_view3",
                "filter_group": [11, 12, 13, 14],
            }),
            content_type='application/json'
        )
        data = json.loads(response.content)
        self.assertEqual('error', data['status'])
        expected = 'Data Validation Error'
        self.assertEqual(expected, data['message'])

    def test_data_view_retreive_endpoint(self):
        response = self.client.get(
            reverse('api:v3:data_views-detail', args=[self.data_view1.id]) + '?organization_id=' + str(self.org.id)
        )

        data = json.loads(response.content)
        self.assertEqual('success', data['status'])
        self.assertEqual('data view 1', data['data_view']['name'])

        response = self.client.get(
            reverse('api:v3:data_views-detail', args=[99999999]) + '?organization_id=' + str(self.org.id)
        )
        data = json.loads(response.content)
        self.assertEqual('error', data['status'])
        self.assertEqual('DataView with id 99999999 does not exist', data['message'])

    def test_data_view_update_endpoint(self):
        self.assertEqual('data view 1', self.data_view1.name)
        self.assertEqual(2, len(self.data_view1.columns.all()))

        response = self.client.put(
            reverse('api:v3:data_views-detail', args=[self.data_view1.id]) + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                "name": "updated name",
            }),
            content_type='application/json'
        )

        data = json.loads(response.content)
        self.assertEqual('success', data['status'])
        self.assertEqual('updated name', data['data_view']['name'])

        data_view1 = DataView.objects.get(id=self.data_view1.id)
        self.assertEqual('updated name', data_view1.name)

        response = self.client.put(
            reverse('api:v3:data_views-detail', args=[self.data_view1.id]) + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                "columns": [self.column1.id, self.column2.id, self.column3.id],
            }),
            content_type='application/json'
        )
        data = json.loads(response.content)
        data_view1 = DataView.objects.get(id=self.data_view1.id)
        self.assertEqual('updated name', data_view1.name)
        self.assertEqual(3, len(data_view1.columns.all()))

        response = self.client.put(
            reverse('api:v3:data_views-detail', args=[99999]) + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                "columns": [self.column1.id, self.column2.id, self.column3.id],
            }),
            content_type='application/json'
        )
        data = json.loads(response.content)
        self.assertEqual('error', data['status'])
        self.assertEqual('DataView with id 99999 does not exist', data['message'])
