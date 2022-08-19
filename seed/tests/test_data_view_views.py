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
from pint import UnitRegistry

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
from django.http import QueryDict


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
            filter_groups=[1, 2, 3, 4], 
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
            filter_groups=[5, 6, 7, 8], 
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
        self.assertEqual([1, 2, 3, 4], data_view1.filter_groups)
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
        self.assertEqual([1, 2, 3, 4], data_view1.filter_groups)
        self.assertEqual(1, len(data_view2.parameters.all()))

        
        parameter3 = data_view2.parameters.first()
        self.assertEqual(self.column3, parameter3.column)
        self.assertEqual(['Avg', 'Max', 'Sum'], parameter3.aggregations)
        self.assertEqual('axis1', parameter3.location)
        self.assertEqual('col_3_target', parameter3.target)

    def test_data_view_create_endpoint(self):
        self.assertEqual(2, len(DataView.objects.all()))
        self.assertEqual(3, len(DataViewParameter.objects.all()))

        response = self.client.get(
            reverse('api:v3:data_views-list') + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )

        self.assertEqual(2, len(json.loads(response.content)['message']))

        response = self.client.post(
            reverse('api:v3:data_views-list') + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                "name": "data_view3",
                "filter_groups": [11, 12, 13, 14],
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

        self.assertEqual(3, len(DataView.objects.all()))
        self.assertEqual(5, len(DataViewParameter.objects.all()))

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
        self.assertEqual(2, len(DataView.objects.all()))
        self.assertEqual(3, len(DataViewParameter.objects.all()))


    def test_data_view_create_bad_data(self):
        response = self.client.post(
            reverse('api:v3:data_views-list') + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                "name": "data_view3",
                "filter_groups": [11, 12, 13, 14]
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
        self.assertEqual(3, len(DataViewParameter.objects.all()))
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

        self.assertEqual(2, len(DataViewParameter.objects.all()))

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

        # generate columns
        self.site_eui = Column.objects.get(column_name='site_eui')
        self.ghg = Column.objects.get(column_name='total_ghg_emissions')
        self.extra_col = Column.objects.create(column_name='extra_col', organization=self.org, is_extra_data=True, table_name='PropertyState')

        
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)     

        # generate two different types of properties
        self.office1 = self.property_factory.get_property()
        self.office2 = self.property_factory.get_property()
        self.retail3 = self.property_factory.get_property()
        self.retail4 = self.property_factory.get_property()


        # define some eui values
        ureg = UnitRegistry()
        ureg.eui = ureg.eui = ureg.kilobritish_thermal_unit / ureg.ft**2 / ureg.year

        # generate property states that are either 'Office' or 'Retail' for filter groups
        # generate property views that are attatched to a property and a property-state
        self.st_office10 = self.property_state_factory.get_property_state(property_name='st_office10', property_type='office', site_eui=10*ureg.eui, total_ghg_emissions=100, extra_data={'extra_col':100})
        self.st_office11 = self.property_state_factory.get_property_state(property_name='st_office11', property_type='office', site_eui=11*ureg.eui, total_ghg_emissions=110, extra_data={'extra_col':110})
        self.st_retail12 = self.property_state_factory.get_property_state(property_name='st_retail12', property_type='retail', site_eui=12*ureg.eui, total_ghg_emissions=120, extra_data={'extra_col':120})
        self.st_retail13 = self.property_state_factory.get_property_state(property_name='st_retail13', property_type='retail', site_eui=13*ureg.eui, total_ghg_emissions=130, extra_data={'extra_col':0})

        self.vw_office10 = PropertyView.objects.create(property=self.office1, cycle=self.cycle1, state=self.st_office10)
        self.vw_office11 = PropertyView.objects.create(property=self.office2, cycle=self.cycle1, state=self.st_office11)
        self.vw_retail13 = PropertyView.objects.create(property=self.retail3, cycle=self.cycle1, state=self.st_retail12)
        self.vw_retail14 = PropertyView.objects.create(property=self.retail4, cycle=self.cycle1, state=self.st_retail13)


        self.st_office20 = self.property_state_factory.get_property_state(property_name='st_office20', property_type='office', site_eui=20*ureg.eui, total_ghg_emissions=200, extra_data={'extra_col':200})
        self.st_office21 = self.property_state_factory.get_property_state(property_name='st_office21', property_type='office', site_eui=21*ureg.eui, total_ghg_emissions=210, extra_data={'extra_col':210})
        self.st_retail22 = self.property_state_factory.get_property_state(property_name='st_retail22', property_type='retail', site_eui=22*ureg.eui, total_ghg_emissions=220, extra_data={'extra_col':220})
        self.st_retail23 = self.property_state_factory.get_property_state(property_name='st_retail23', property_type='retail', site_eui=23*ureg.eui, total_ghg_emissions=230, extra_data={'extra_col':0})

        self.vw_office20 = PropertyView.objects.create(property=self.office1, cycle=self.cycle2, state=self.st_office20)
        self.vw_office21 = PropertyView.objects.create(property=self.office2, cycle=self.cycle2, state=self.st_office21)
        self.vw_retial22 = PropertyView.objects.create(property=self.retail3, cycle=self.cycle2, state=self.st_retail22)
        self.vw_retail23 = PropertyView.objects.create(property=self.retail4, cycle=self.cycle2, state=self.st_retail23)

        self.st_office30 = self.property_state_factory.get_property_state(property_name='st_office30', property_type='office', site_eui=30*ureg.eui, total_ghg_emissions=300, extra_data={'extra_col':300})
        self.st_office31 = self.property_state_factory.get_property_state(property_name='st_office31', property_type='office', site_eui=31*ureg.eui, total_ghg_emissions=310, extra_data={'extra_col':310})
        self.st_retail32 = self.property_state_factory.get_property_state(property_name='st_retail32', property_type='retail', site_eui=32*ureg.eui, total_ghg_emissions=320, extra_data={'extra_col':320})
        self.st_retail33 = self.property_state_factory.get_property_state(property_name='st_retail33', property_type='retail', site_eui=33*ureg.eui, total_ghg_emissions=330, extra_data={'extra_col':0})

        self.vw_office30 = PropertyView.objects.create(property=self.office1, cycle=self.cycle3, state=self.st_office30)
        self.vw_office31 = PropertyView.objects.create(property=self.office2, cycle=self.cycle3, state=self.st_office31)
        self.vw_retail32 = PropertyView.objects.create(property=self.retail3, cycle=self.cycle3, state=self.st_retail32)
        self.vw_retail33 = PropertyView.objects.create(property=self.retail4, cycle=self.cycle3, state=self.st_retail33)

        self.st_office40 = self.property_state_factory.get_property_state(property_name='st_office40', property_type='office', site_eui=40*ureg.eui, total_ghg_emissions=400, extra_data={'extra_col':400})
        self.st_office41 = self.property_state_factory.get_property_state(property_name='st_office41', property_type='office', site_eui=41*ureg.eui, total_ghg_emissions=410, extra_data={'extra_col':410})
        self.st_retail42 = self.property_state_factory.get_property_state(property_name='st_retail42', property_type='retail', site_eui=42*ureg.eui, total_ghg_emissions=420, extra_data={'extra_col':420})
        self.st_retail43 = self.property_state_factory.get_property_state(property_name='st_retail43', property_type='retail', site_eui=43*ureg.eui, total_ghg_emissions=430, extra_data={'extra_col':0})

        self.vw_office40 = PropertyView.objects.create(property=self.office1, cycle=self.cycle4, state=self.st_office40)
        self.vw_office41 = PropertyView.objects.create(property=self.office2, cycle=self.cycle4, state=self.st_office41)
        self.vw_retail42 = PropertyView.objects.create(property=self.retail3, cycle=self.cycle4, state=self.st_retail42)
        self.vw_retail43 = PropertyView.objects.create(property=self.retail4, cycle=self.cycle4, state=self.st_retail43)

        self.data_view1 = DataView.objects.create(
            name='data view 1', 
            filter_groups=[
                {'name': 'office', 'query_dict': QueryDict('property_type__exact=office&site_eui__gt=1')},
                {'name': 'retail', 'query_dict': QueryDict('property_type__exact=retail&site_eui__gt=1')}
                ], 
            organization=self.org)
        self.data_view1.cycles.set([self.cycle1, self.cycle3, self.cycle4])
        self.data_view1_parameter1 = DataViewParameter.objects.create(
            data_view = self.data_view1,
            column = self.site_eui,
            aggregations = ['Avg', 'Sum'],
            location='axis1', 
        )
        self.data_view1_parameter2 = DataViewParameter.objects.create(
            data_view = self.data_view1,
            column = self.ghg,
            aggregations = ['Max', 'Min'],
            location='axis2', 
            target='test'
        )

        self.data_view2 = DataView.objects.create(
            name='data view 2', 
            filter_groups=[
                {'name': '3_properties', 'query_dict': QueryDict('extra_col__gt=1&site_eui__gt=1')},
                {'name': '4_properties', 'query_dict': QueryDict('site_eui__gt=1')}
                ], 
            organization=self.org)
        self.data_view2.cycles.set([self.cycle1, self.cycle2, self.cycle3, self.cycle4])
        self.data_view2_parameter1 = DataViewParameter.objects.create(
            data_view = self.data_view2,
            column = self.extra_col,
            aggregations = ['Avg'],
            location='axis1', 
        )

    # @unittest.skip
    def test_evaluation_endpoint_canonical_col(self):

        self.assertEqual(4, len(self.cycle1.propertyview_set.all()))
        self.assertEqual(4, len(self.cycle2.propertyview_set.all()))
        self.assertEqual(4, len(self.cycle3.propertyview_set.all()))
        self.assertEqual(4, len(self.cycle4.propertyview_set.all()))

        response = self.client.get(
            reverse('api:v3:data_views-evaluate', args=[self.data_view1.id]) + '?organization_id=' + str(self.org.id)
        )

        data = json.loads(response.content)
        self.assertEqual('success', data['status'])
        breakpoint()

        data = data['data']
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

    @unittest.skip
    def test_evaluation_endpoint_extra_col(self):
        response = self.client.get(
            reverse('api:v3:data_views-evaluate', args=[self.data_view2.id]) + '?organization_id=' + str(self.org.id)
        )
        data = json.loads(response.content)

        breakpoint()