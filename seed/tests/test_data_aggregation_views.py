# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
import json
from django.test import TestCase
from django.urls import reverse
from seed.models import DataAggregation, User, Column
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

        self.column1 = Column.objects.create(
            column_name='column 1',
            organization=self.org,
        )
        self.data_aggregation_1 = DataAggregation.objects.create(
            name='column1 max',
            column=self.column1,
            type=2,
            organization=self.org
        )
        self.data_aggregation_2 = DataAggregation.objects.create(
            name='column1 min',
            column=self.column1,
            type=3,
            organization=self.org
        )

    def test_data_aggregation_model(self):
        data_aggregations = DataAggregation.objects.all()
        self.assertEqual(len(data_aggregations), 2) 

        self.assertEqual(data_aggregations[0].name,'column1 max')
        self.assertEqual(data_aggregations[0].column_id, self.column1.id )
        self.assertEqual(data_aggregations[0].type, 2)

        self.assertEqual(data_aggregations[1].name,'column1 min')
        self.assertEqual(data_aggregations[1].column_id, self.column1.id )
        self.assertEqual(data_aggregations[1].type, 3)



    def test_data_aggregation_create_endpoint(self):
        self.assertEqual(len(DataAggregation.objects.all()), 2)

        self.client.post(
            reverse('api:v3:data_aggregations-list') + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                "name": "column 1 sum",
                "type": "Sum",
                "column": self.column1.id
            }),
            content_type='application/json'
        )

        self.assertEqual(len(DataAggregation.objects.all()), 3)
        self.assertEqual(DataAggregation.objects.get(name='column 1 sum').name, 'column 1 sum')



    def test_data_aggregation_list_endpoint(self):
        self.assertEqual(len(DataAggregation.objects.all()), 2)
        
        response = self.client.get(
            reverse('api:v3:data_aggregations-list') + '?organization_id=' + str(self.org.id)
        )
        data = json.loads(response.content)

        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['message']), 2)
        self.assertEqual(list(data['message'][0].keys()), ['id', 'type', 'name', 'column', 'organization'])
        self.assertEqual(list(data['message'][1].keys()), ['id', 'type', 'name', 'column', 'organization'])

    def test_data_aggregation_retreive_endpoint(self):
        response = self.client.get(
            reverse('api:v3:data_aggregations-detail', args=[self.data_aggregation_1.id]) + '?organization_id=' + str(self.org.id)
            )

        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data_aggregation']['name'], 'column1 max')
        
        response = self.client.get(
            reverse('api:v3:data_aggregations-detail', args=[self.data_aggregation_2.id]) + '?organization_id=' + str(self.org.id)
        )

        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data_aggregation']['name'], 'column1 min')


    def test_data_aggregation_update_endpoint(self):
        id_1 = self.data_aggregation_1.id
        self.assertEqual(self.data_aggregation_1.name, 'column1 max')

        response = self.client.put(
            reverse('api:v3:data_aggregations-detail', args=[self.data_aggregation_1.id]) + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                "name": "updated name",
            }),
            content_type='application/json'
            
        )

        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        data_aggregation_1 = DataAggregation.objects.get(id=id_1)
        self.assertEqual(data_aggregation_1.name, 'updated name')

    def test_data_aggregation_delete_endpoint(self):
        id_1 = self.data_aggregation_1.id
        id_2 = self.data_aggregation_2.id
        self.assertEqual(len(DataAggregation.objects.all()), 2)
        
        response = self.client.delete(
            reverse('api:v3:data_aggregations-detail',  args=[id_1]) + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )

        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(DataAggregation.objects.all()), 1)

        response = self.client.get(
            reverse('api:v3:data_aggregations-detail', args=[id_1]) + '?organization_id=' + str(self.org.id)
        )
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'error')
        response = self.client.get(
            reverse('api:v3:data_aggregations-detail', args=[id_2]) + '?organization_id=' + str(self.org.id)
        )
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
