# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
import json

from django.test import TestCase
from django.urls import reverse
from datetime import datetime
import pytz
import unittest

from seed.models import (
    Column,
    DataView,
    DataViewParameter,
    User,
    Property,
    PropertyState,
    PropertyView
    )
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
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
        self.cycle1 = FakeCycleFactory(organization=self.org, user=self.user).get_cycle(name="Cycle A")
        self.cycle2 = FakeCycleFactory(organization=self.org, user=self.user).get_cycle(name="Cycle B")
        self.cycle3 = FakeCycleFactory(organization=self.org, user=self.user).get_cycle(name="Cycle C")
        self.cycle4 = FakeCycleFactory(organization=self.org, user=self.user).get_cycle(name="Cycle D")

        self.column1 = Column.objects.create(column_name='column 1', organization=self.org,)
        self.column2 = Column.objects.create(column_name='column 2', organization=self.org,)
        self.column3 = Column.objects.create(column_name='column 3', organization=self.org,)

        self.data_view1 = DataView.objects.create(
            name='data view 1', 
            organization=self.org, 
            filter_group=[1, 2, 3, 4], 
            )
        # self.data_view1.columns.set([self.column1, self.column2])
        self.data_view1.cycles.set([self.cycle1, self.cycle3, self.cycle4])

        self.data_view1_parameter1 = DataViewParameter.objects.create(
            data_view = self.data_view1,
            column = self.column1,
            aggregations = ['Avg', 'Sum'],
            location='axis1', 
        )
        self.data_view1_parameter2 = DataViewParameter.objects.create(
            data_view = self.data_view1,
            column = self.column2,
            aggregations = ['Max', 'Min'],
            location='axis2', 
        )

        self.data_view2 = DataView.objects.create(
            name='data view 2', 
            organization=self.org,
            filter_group=[5, 6, 7, 8], 
            )
        # self.data_view2.columns.set([self.column1, self.column2, self.column3])
        self.data_view2.cycles.set([self.cycle2, self.cycle4])
        self.data_view2_parameter1 = DataViewParameter.objects.create(
            data_view = self.data_view2,
            column = self.column3,
            aggregations = ['Avg', 'Max', 'Sum'],
            location='axis1',
            target='col_3_target' 
        )

    def test_data_view_model(self):
        data_views = DataView.objects.all()
        self.assertEqual(2, len(data_views))

        data_view1 = data_views[0]
        self.assertEqual([1, 2, 3, 4], data_view1.filter_group)
        self.assertEqual(2, len(data_view1.parameters.all()))

        parameter1 = data_view1.parameters.first()
        self.assertEqual(self.column1, parameter1.column)
        self.assertEqual(['Avg', 'Sum'], parameter1.aggregations)
        self.assertEqual('axis1', parameter1.location)

        parameter2 = data_view1.parameters.last()
        self.assertEqual(self.column2, parameter2.column)
        self.assertEqual(['Max', 'Min'], parameter2.aggregations)
        self.assertEqual('axis2', parameter2.location)


        data_view2 = data_views[1]
        self.assertEqual([1, 2, 3, 4], data_view1.filter_group)
        self.assertEqual(1, len(data_view2.parameters.all()))

        
        parameter3 = data_view2.parameters.first()
        self.assertEqual(self.column3, parameter3.column)
        self.assertEqual(['Avg', 'Max', 'Sum'], parameter3.aggregations)
        self.assertEqual('axis1', parameter3.location)
        self.assertEqual('col_3_target', parameter3.target)

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
                "cycles": [self.cycle1.id, self.cycle2.id, self.cycle3.id],
                "parameters": [
                    {
                        "column": self.column1.id,
                        "location": 'axis 1',
                        "aggregations": ['Avg'],
                    },
                    {
                        "column": self.column2.id,
                        "location": 'axis 2',
                        "aggregations": ['Max', 'Sum'],
                        "target": "abc"
                    }
                ]

            }),
            content_type='application/json'
        )
        data = json.loads(response.content)

        self.assertEqual('data_view3', data['data_view']['name'])
        self.assertEqual(self.org.id, data['data_view']['organization'])
        self.assertTrue(bool(data['data_view']['id']))
        self.assertEqual(self.column1.id, data['data_view']['parameters'][0]['column'])
        self.assertEqual(['Avg'], data['data_view']['parameters'][0]['aggregations'])
        self.assertEqual('axis 1', data['data_view']['parameters'][0]['location'])
        self.assertEqual(self.column2.id, data['data_view']['parameters'][1]['column'])
        self.assertEqual(['Max', 'Sum'], data['data_view']['parameters'][1]['aggregations'])
        self.assertEqual('axis 2', data['data_view']['parameters'][1]['location'])
        self.assertEqual('abc', data['data_view']['parameters'][1]['target'])

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
                "filter_group": [11, 12, 13, 14]
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
        self.assertEqual('axis1', data['data_view']['parameters'][0]['location'])

        response = self.client.get(
            reverse('api:v3:data_views-detail', args=[99999999]) + '?organization_id=' + str(self.org.id)
        )
        data = json.loads(response.content)
        self.assertEqual('error', data['status'])
        self.assertEqual('DataView with id 99999999 does not exist', data['message'])


    def test_data_view_update_endpoint(self):
        self.assertEqual('data view 1', self.data_view1.name)
        self.assertEqual(2, len(self.data_view1.parameters.all()))
        self.assertEqual('axis1', self.data_view1.parameters.first().location)

        response = self.client.put(
            reverse('api:v3:data_views-detail', args=[self.data_view1.id]) + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                "name": "updated name",
                "parameters": [
                    {
                        "column": self.column3.id,
                        "location": 'new location',
                        "aggregations": ['Sum'],
                    }
                ]
            }),
            content_type='application/json'
        )

        data = json.loads(response.content)
        self.assertEqual('success', data['status'])
        self.assertEqual('updated name', data['data_view']['name'])
        self.assertEqual(1, len(data['data_view']['parameters']))
        self.assertEqual('new location', data['data_view']['parameters'][0]['location'])

        data_view1 = DataView.objects.get(id=self.data_view1.id)
        self.assertEqual('updated name', data_view1.name)
        self.assertEqual(1, len(data_view1.parameters.all()))
        self.assertEqual('new location', data_view1.parameters.first().location)

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



class DataViewEvaluationTests(TestCase):
    """
    Test DataView model's ability to evaluate propertystate values based on attributes
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
        self.cycle1 = FakeCycleFactory(organization=self.org, user=self.user).get_cycle(name="Cycle A", end=datetime(2022, 1, 1, tzinfo=pytz.UTC))
        self.cycle2 = FakeCycleFactory(organization=self.org, user=self.user).get_cycle(name="Cycle B", end=datetime(2021, 1, 1, tzinfo=pytz.UTC))
        self.cycle3 = FakeCycleFactory(organization=self.org, user=self.user).get_cycle(name="Cycle C", end=datetime(2020, 1, 1, tzinfo=pytz.UTC))
        self.cycle4 = FakeCycleFactory(organization=self.org, user=self.user).get_cycle(name="Cycle D", end=datetime(2019, 1, 1, tzinfo=pytz.UTC))

        self.site_eui = Column.objects.get(column_name='site_eui')
        self.ghg = Column.objects.get(column_name='total_ghg_emissions')
        self.floor_area = Column.objects.get(column_name='occupied_floor_area')

        self.data_view1 = DataView.objects.create(name='data view 1', filter_group=[1, 2, 3, 4], organization=self.org)
        self.data_view1.columns.set([self.site_eui, self.ghg])
        self.data_view1.cycles.set([self.cycle1, self.cycle3, self.cycle4])

        self.data_view2 = DataView.objects.create(name='data view 2', filter_group=[5, 6, 7, 8], organization=self.org)
        self.data_view2.columns.set([self.site_eui, self.ghg, self.floor_area])
        self.data_view2.cycles.set([self.cycle2, self.cycle4])

        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)     

        self.property1 = self.property_factory.get_property()
        self.property2 = self.property_factory.get_property()
        self.property3 = self.property_factory.get_property()
        self.property4 = self.property_factory.get_property()

        self.state10 = self.property_state_factory.get_property_state(
            property_name='state10',
            site_eui=10,
            total_ghg_emissions=100,
        )
        self.state11 = self.property_state_factory.get_property_state(
            property_name='state11',
            site_eui=11,
            total_ghg_emissions=110,
        )
        self.state12 = self.property_state_factory.get_property_state(
            property_name='state12',
            site_eui=12,
            total_ghg_emissions=120,
        )
        self.state13 = self.property_state_factory.get_property_state(
            property_name='state13',
            site_eui=13,
            total_ghg_emissions=130,
        )

        self.view10 = PropertyView.objects.create(property=self.property1, cycle=self.cycle1, state=self.state10)
        self.view11 = PropertyView.objects.create(property=self.property2, cycle=self.cycle1, state=self.state11)
        self.view12 = PropertyView.objects.create(property=self.property3, cycle=self.cycle1, state=self.state12)
        self.view13 = PropertyView.objects.create(property=self.property4, cycle=self.cycle1, state=self.state13)


        self.state20 = self.property_state_factory.get_property_state(
            property_name='state20',
            site_eui=20,
            total_ghg_emissions=200,
        )
        self.state21 = self.property_state_factory.get_property_state(
            property_name='state21',
            site_eui=21,
            total_ghg_emissions=210,
        )
        self.state22 = self.property_state_factory.get_property_state(
            property_name='state22',
            site_eui=22,
            total_ghg_emissions=220,
        )
        self.state23 = self.property_state_factory.get_property_state(
            property_name='state23',
            site_eui=23,
            total_ghg_emissions=230,
        )

        self.view20 = PropertyView.objects.create(property=self.property1, cycle=self.cycle2, state=self.state20)
        self.view21 = PropertyView.objects.create(property=self.property2, cycle=self.cycle2, state=self.state21)
        self.view22 = PropertyView.objects.create(property=self.property3, cycle=self.cycle2, state=self.state22)
        self.view23 = PropertyView.objects.create(property=self.property4, cycle=self.cycle2, state=self.state23)

        self.state30 = self.property_state_factory.get_property_state(
            property_name='state30',
            site_eui=30,
            total_ghg_emissions=300,
        )
        self.state31 = self.property_state_factory.get_property_state(
            property_name='state31',
            site_eui=31,
            total_ghg_emissions=310,
        )
        self.state32 = self.property_state_factory.get_property_state(
            property_name='state32',
            site_eui=32,
            total_ghg_emissions=320,
        )
        self.state33 = self.property_state_factory.get_property_state(
            property_name='state33',
            site_eui=33,
            total_ghg_emissions=330,
        )

        self.view30 = PropertyView.objects.create(property=self.property1, cycle=self.cycle3, state=self.state30)
        self.view31 = PropertyView.objects.create(property=self.property2, cycle=self.cycle3, state=self.state31)
        self.view32 = PropertyView.objects.create(property=self.property3, cycle=self.cycle3, state=self.state32)
        self.view33 = PropertyView.objects.create(property=self.property4, cycle=self.cycle3, state=self.state33)

        self.state40 = self.property_state_factory.get_property_state(
            property_name='state40',
            site_eui=40,
            total_ghg_emissions=400,
        )
        self.state41 = self.property_state_factory.get_property_state(
            property_name='state41',
            site_eui=41,
            total_ghg_emissions=410,
        )
        self.state42 = self.property_state_factory.get_property_state(
            property_name='state42',
            site_eui=42,
            total_ghg_emissions=420,
        )
        self.state43 = self.property_state_factory.get_property_state(
            property_name='state43',
            site_eui=43,
            total_ghg_emissions=430,
        )

        self.view40 = PropertyView.objects.create(property=self.property1, cycle=self.cycle4, state=self.state40)
        self.view41 = PropertyView.objects.create(property=self.property2, cycle=self.cycle4, state=self.state41)
        self.view42 = PropertyView.objects.create(property=self.property3, cycle=self.cycle4, state=self.state42)
        self.view43 = PropertyView.objects.create(property=self.property4, cycle=self.cycle4, state=self.state43)

    @unittest.skip
    def test_evaluation_endpoint(self):

        self.assertEqual(4, len(self.cycle1.propertyview_set.all()))
        self.assertEqual(4, len(self.cycle2.propertyview_set.all()))
        self.assertEqual(4, len(self.cycle3.propertyview_set.all()))
        self.assertEqual(4, len(self.cycle4.propertyview_set.all()))

        response = self.client.get(
            reverse('api:v3:data_views-evaluate', args=[self.data_view1.id]) + '?organization_id=' + str(self.org.id)
        )

        data = json.loads(response.content)
        self.assertEqual('success', data['status'])

        data = data['message']
        self.assertEqual(['meta', 'data'], list(data.keys()))
        self.assertEqual(1, data['meta']['data_view'])
        self.assertEqual(1, data['meta']['organization'])

        data = data['data']
        self.assertEqual(['2019-01-01', '2020-01-01', '2022-01-01'], list(data.keys()))

        data = data['2019-01-01']
        self.assertEqual(['site_eui', 'total_ghg_emissions'], list(data.keys()))

        data = data['site_eui']
        self.assertEqual(['views_by_id', 'units', 'eui avg', 'eui sum'], list(data.keys()))

        expected = {'13': 40.0, '14': 41.0, '15': 42.0, '16': 43.0}
        self.assertEqual(expected, data['views_by_id'])