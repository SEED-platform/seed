# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
import json
from datetime import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import get_current_timezone

from seed.models import (
    Column,
    Cycle,
    DataAggregation,
    DataView,
    DerivedColumn,
    PropertyView,
    User
)
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakeDerivedColumnFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory
)
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
        self.cycle1 = FakeCycleFactory(organization=self.org,user=self.user).get_cycle(name="Cycle A")
        self.cycle2 = FakeCycleFactory(organization=self.org,user=self.user).get_cycle(name="Cycle B")
        self.cycle3 = FakeCycleFactory(organization=self.org,user=self.user).get_cycle(name="Cycle C")
        self.cycle4 = FakeCycleFactory(organization=self.org,user=self.user).get_cycle(name="Cycle D")

        self.column1 = Column.objects.create(column_name='column 1',organization=self.org,)
        self.column2 = Column.objects.create(column_name='column 2',organization=self.org,)
        self.column3 = Column.objects.create(column_name='column 3',organization=self.org,)
        
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

        self.data_view_1 = DataView.objects.create(name='data view 1', filter_group=[1,2,3,4], organization=self.org)
        self.data_view_1.columns.set([self.column1, self.column2])
        self.data_view_1.cycles.set([self.cycle1, self.cycle3, self.cycle4])
        self.data_view_1.data_aggregations.set([self.data_aggregation2, self.data_aggregation3])

        self.data_view_2 = DataView.objects.create(name='data view 2', filter_group=[5,6,7,8], organization=self.org)
        self.data_view_2.columns.set([self.column1, self.column2 , self.column3])
        self.data_view_2.cycles.set([self.cycle2, self.cycle4])
        self.data_view_2.data_aggregations.set([self.data_aggregation1, self.data_aggregation2, self.data_aggregation3])

    # Test not needed
    def test_SetUp(self):
        cycles = Cycle.objects.all()
        self.assertEqual(6, len(cycles))

        columns = Column.objects.all()
        self.assertEqual(77, len(columns))

        data_aggs = DataAggregation.objects.all()
        self.assertEqual(3, len(data_aggs))

        data_views = DataView.objects.all()
        self.assertEqual(2, len(data_views))
        data_view = data_views[0]
        self.assertEqual(2, len(data_view.columns.all()))
        self.assertEqual(3, len(data_view.cycles.all()))
        self.assertEqual(2, len(data_view.data_aggregations.all()))
        self.assertEqual([1,2,3,4], data_view.filter_group)

    def test_data_view_model(self):
        data_views = DataView.objects.all()
        self.assertEqual(2, len(data_views))

        data_view_1 = data_views[0]
        self.assertEqual(2, len(data_view_1.columns.all()))
        self.assertEqual(3, len(data_view_1.cycles.all()))
        self.assertEqual(2, len(data_view_1.data_aggregations.all()))
        self.assertEqual([1, 2, 3, 4], data_view_1.filter_group)

        data_view_2 = data_views[1]
        self.assertEqual(3, len(data_view_2.columns.all()))
        self.assertEqual(2, len(data_view_2.cycles.all()))
        self.assertEqual(3, len(data_view_2.data_aggregations.all()))
        self.assertEqual([5, 6, 7, 8], data_view_2.filter_group)

    def test_data_view_create_endpoint(self):
        self.assertEqual(2, len(DataView.objects.all()))

        api_res = self.client.get(
            reverse('api:v3:data_view-list') + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )
        breakpoint()

        self.client.post(
            reverse('api:v3:data_view-list') + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                "name": "data_view3",
                "filter_group": [11, 12, 13, 14],
                "columns": [self.column1, self.column2, self.column3],
                "cycles": [self.cycle1, self.cycle2, self.cycle3],
                "data_aggregations":[self.data_aggregation1, self.data_aggregation2]
                
            }),
            content_type='application/json'
        )