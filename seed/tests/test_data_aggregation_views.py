# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
import json
from django.test import TestCase
from django.urls import reverse, reverse_lazy
from seed.models import DataAggregation, User, Organization, Column
from seed.utils.organizations import create_organization



class DataAggregationViewTests(TestCase):
    """
    Test DataAggregation model
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

        column1 = Column.objects.create(
            column_name='column 1',
            organization=self.org,
        )
        DataAggregation.objects.create(
            name='column1 max',
            column=column1,
            type=3
        )

    def test_data_aggregation_creation(self):
        data_aggregations = DataAggregation.objects.all()
        self.assertEqual(len(data_aggregations), 1) 

        data_aggregation = data_aggregations[0]
        self.assertEqual(data_aggregation.name,'column1 max')
        column_id = Column.objects.get(column_name='column 1').id
        self.assertEqual(data_aggregation.column_id, column_id )
        self.assertEqual(data_aggregation.type, 3)



    def test_create_data_aggregation(self):
        breakpoint()
        url = reverse('api:v3:data_aggregation', args=[])
        response = self.client.post(reverse(url, content_type='application/json'))
        # breakpoint()
