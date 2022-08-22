# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
import json
from datetime import datetime

import pytz
from django.http import QueryDict
from django.test import TestCase
from django.urls import reverse
from pint import UnitRegistry

from seed.models import (
    Column,
    DataView,
    DataViewParameter,
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
        self.st_office10 = self.property_state_factory.get_property_state(property_name='st_office10', property_type='office', site_eui=10*ureg.eui, total_ghg_emissions=100, extra_data={'extra_col':1000})
        self.st_office11 = self.property_state_factory.get_property_state(property_name='st_office11', property_type='office', site_eui=11*ureg.eui, total_ghg_emissions=110, extra_data={'extra_col':1100})
        self.st_retail12 = self.property_state_factory.get_property_state(property_name='st_retail12', property_type='retail', site_eui=12*ureg.eui, total_ghg_emissions=120, extra_data={'extra_col':1200})
        self.st_retail13 = self.property_state_factory.get_property_state(property_name='st_retail13', property_type='retail', site_eui=13*ureg.eui, total_ghg_emissions=130, extra_data={'extra_col':0})

        self.vw_office10 = PropertyView.objects.create(property=self.office1, cycle=self.cycle1, state=self.st_office10)
        self.vw_office11 = PropertyView.objects.create(property=self.office2, cycle=self.cycle1, state=self.st_office11)
        self.vw_retail12 = PropertyView.objects.create(property=self.retail3, cycle=self.cycle1, state=self.st_retail12)
        self.vw_retail13 = PropertyView.objects.create(property=self.retail4, cycle=self.cycle1, state=self.st_retail13)


        self.st_office20 = self.property_state_factory.get_property_state(property_name='st_office20', property_type='office', site_eui=20*ureg.eui, total_ghg_emissions=200, extra_data={'extra_col':2000})
        self.st_office21 = self.property_state_factory.get_property_state(property_name='st_office21', property_type='office', site_eui=21*ureg.eui, total_ghg_emissions=210, extra_data={'extra_col':2100})
        self.st_retail22 = self.property_state_factory.get_property_state(property_name='st_retail22', property_type='retail', site_eui=22*ureg.eui, total_ghg_emissions=220, extra_data={'extra_col':2200})
        self.st_retail23 = self.property_state_factory.get_property_state(property_name='st_retail23', property_type='retail', site_eui=23*ureg.eui, total_ghg_emissions=230, extra_data={'extra_col':0})

        self.vw_office20 = PropertyView.objects.create(property=self.office1, cycle=self.cycle2, state=self.st_office20)
        self.vw_office21 = PropertyView.objects.create(property=self.office2, cycle=self.cycle2, state=self.st_office21)
        self.vw_retail22 = PropertyView.objects.create(property=self.retail3, cycle=self.cycle2, state=self.st_retail22)
        self.vw_retail23 = PropertyView.objects.create(property=self.retail4, cycle=self.cycle2, state=self.st_retail23)

        self.st_office30 = self.property_state_factory.get_property_state(property_name='st_office30', property_type='office', site_eui=30*ureg.eui, total_ghg_emissions=300, extra_data={'extra_col':3000})
        self.st_office31 = self.property_state_factory.get_property_state(property_name='st_office31', property_type='office', site_eui=31*ureg.eui, total_ghg_emissions=310, extra_data={'extra_col':3100})
        self.st_retail32 = self.property_state_factory.get_property_state(property_name='st_retail32', property_type='retail', site_eui=32*ureg.eui, total_ghg_emissions=320, extra_data={'extra_col':3200})
        self.st_retail33 = self.property_state_factory.get_property_state(property_name='st_retail33', property_type='retail', site_eui=33*ureg.eui, total_ghg_emissions=330, extra_data={'extra_col':0})

        self.vw_office30 = PropertyView.objects.create(property=self.office1, cycle=self.cycle3, state=self.st_office30)
        self.vw_office31 = PropertyView.objects.create(property=self.office2, cycle=self.cycle3, state=self.st_office31)
        self.vw_retail32 = PropertyView.objects.create(property=self.retail3, cycle=self.cycle3, state=self.st_retail32)
        self.vw_retail33 = PropertyView.objects.create(property=self.retail4, cycle=self.cycle3, state=self.st_retail33)

        self.st_office40 = self.property_state_factory.get_property_state(property_name='st_office40', property_type='office', site_eui=40*ureg.eui, total_ghg_emissions=400, extra_data={'extra_col':4000})
        self.st_office41 = self.property_state_factory.get_property_state(property_name='st_office41', property_type='office', site_eui=41*ureg.eui, total_ghg_emissions=410, extra_data={'extra_col':4100})
        self.st_retail42 = self.property_state_factory.get_property_state(property_name='st_retail42', property_type='retail', site_eui=42*ureg.eui, total_ghg_emissions=420, extra_data={'extra_col':4200})
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
                {'name': 'three_properties', 'query_dict': QueryDict('extra_col__gt=1&site_eui__gt=1')},
                {'name': 'four_properties', 'query_dict': QueryDict('site_eui__gt=1')}
                ],
            organization=self.org)
        self.data_view2.cycles.set([self.cycle1, self.cycle2, self.cycle3, self.cycle4])
        self.data_view2_parameter1 = DataViewParameter.objects.create(
            data_view = self.data_view2,
            column = self.extra_col,
            aggregations = ['Avg'],
            location='axis1',
        )

        # Generate derived column for testing
        self.derived_column = DerivedColumn.objects.create(
            name='dc',
            expression='$a + 10',
            organization=self.org,
            inventory_type=0,
        )
        self.derived_column.source_columns.add(self.site_eui.id)
        self.dcp = self.derived_column.derivedcolumnparameter_set.first()
        self.dcp.parameter_name = 'a'
        self.dcp.save()

        self.derived_col_factory = FakeDerivedColumnFactory(
            organization=self.org,
            inventory_type=DerivedColumn.PROPERTY_TYPE
        )
        self.dc_column = Column.objects.get(column_name='dc')

        self.data_view3 = DataView.objects.create(
            name='data view 3',
            filter_groups=[
                {'name': 'dc_filter', 'query_dict': QueryDict('site_eui__gt=1')},
                ],
            organization=self.org)
        self.data_view3.cycles.set([self.cycle1, self.cycle2])
        self.data_view3_parameter1 = DataViewParameter.objects.create(
            data_view = self.data_view3,
            column = self.dc_column,
            aggregations = ['Avg'],
            location='axis1',
        )


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

        data = data['data']
        self.assertEqual(['meta', 'filter_group_view_ids', 'data'], list(data.keys()))

        self.assertEqual(['organization', 'data_view'], list(data['meta'].keys()))

        self.assertEqual(['office', 'retail'], list(data['filter_group_view_ids']))
        self.assertEqual(['Cycle D', 'Cycle C', 'Cycle A'], list(data['filter_group_view_ids']['office'].keys()))
        self.assertEqual(['Cycle D', 'Cycle C', 'Cycle A'], list(data['filter_group_view_ids']['retail'].keys()))
        office = data['filter_group_view_ids']['office']
        retail = data['filter_group_view_ids']['retail']

        self.assertEqual([self.vw_office10.id, self.vw_office11.id], office['Cycle A'])
        self.assertEqual([self.vw_office30.id, self.vw_office31.id], office['Cycle C'])
        self.assertEqual([self.vw_office40.id, self.vw_office41.id], office['Cycle D'])
        self.assertEqual([self.vw_retail12.id, self.vw_retail13.id], retail['Cycle A'])
        self.assertEqual([self.vw_retail32.id, self.vw_retail33.id], retail['Cycle C'])
        self.assertEqual([self.vw_retail42.id, self.vw_retail43.id], retail['Cycle D'])

        data = data['data']
        self.assertEqual(['site_eui', 'total_ghg_emissions'], list(data.keys()))
        self.assertEqual(['filter_groups', 'unit'], list(data['site_eui'].keys()))
        self.assertEqual('kBtu/ft²/year', data['site_eui']['unit'])
        self.assertEqual('t/year', data['total_ghg_emissions']['unit'])

        office = data['site_eui']['filter_groups']['office']
        retail = data['site_eui']['filter_groups']['retail']
        self.assertEqual(['Avg', 'Max', 'Min', 'Sum', 'Count', 'views_by_id'], list(office.keys()))
        self.assertEqual(['Avg', 'Max', 'Min', 'Sum', 'Count', 'views_by_id'], list(retail.keys()))

        for cycle in office['Avg']:
            self.assertTrue(isinstance(cycle['cycle'], str))
            self.assertTrue(isinstance(cycle['value'], (int, float)))

        self.assertEqual(10.5, [cycle for cycle in office['Avg'] if cycle['cycle'] == 'Cycle A'][0]['value'])
        self.assertEqual(30.5, [cycle for cycle in office['Avg'] if cycle['cycle'] == 'Cycle C'][0]['value'])
        self.assertEqual(40.5, [cycle for cycle in office['Avg'] if cycle['cycle'] == 'Cycle D'][0]['value'])

        self.assertEqual(11, [cycle for cycle in office['Max'] if cycle['cycle'] == 'Cycle A'][0]['value'])
        self.assertEqual(31, [cycle for cycle in office['Max'] if cycle['cycle'] == 'Cycle C'][0]['value'])
        self.assertEqual(41, [cycle for cycle in office['Max'] if cycle['cycle'] == 'Cycle D'][0]['value'])

        self.assertEqual(10, [cycle for cycle in office['Min'] if cycle['cycle'] == 'Cycle A'][0]['value'])
        self.assertEqual(30, [cycle for cycle in office['Min'] if cycle['cycle'] == 'Cycle C'][0]['value'])
        self.assertEqual(40, [cycle for cycle in office['Min'] if cycle['cycle'] == 'Cycle D'][0]['value'])

        self.assertEqual(21, [cycle for cycle in office['Sum'] if cycle['cycle'] == 'Cycle A'][0]['value'])
        self.assertEqual(61, [cycle for cycle in office['Sum'] if cycle['cycle'] == 'Cycle C'][0]['value'])
        self.assertEqual(81, [cycle for cycle in office['Sum'] if cycle['cycle'] == 'Cycle D'][0]['value'])

        self.assertEqual(2, [cycle for cycle in office['Count'] if cycle['cycle'] == 'Cycle A'][0]['value'])
        self.assertEqual(2, [cycle for cycle in office['Count'] if cycle['cycle'] == 'Cycle C'][0]['value'])
        self.assertEqual(2, [cycle for cycle in office['Count'] if cycle['cycle'] == 'Cycle D'][0]['value'])

        exp_ids = [self.vw_office40.id, self.vw_office41.id, self.vw_office30.id, self.vw_office31.id, self.vw_office10.id, self.vw_office11.id]
        exp_ids = [str(id) for id in exp_ids]
        self.assertEqual(exp_ids, list(office['views_by_id'].keys()))

        self.assertEqual(10, office['views_by_id'][str(self.vw_office10.id)][0]['value'])
        self.assertEqual(41, office['views_by_id'][str(self.vw_office41.id)][0]['value'])
        self.assertEqual(12, retail['views_by_id'][str(self.vw_retail12.id)][0]['value'])
        self.assertEqual(42, retail['views_by_id'][str(self.vw_retail42.id)][0]['value'])

        office = data['total_ghg_emissions']['filter_groups']['office']
        self.assertEqual(105, [cycle for cycle in office['Avg'] if cycle['cycle'] == 'Cycle A'][0]['value'])
        self.assertEqual(305, [cycle for cycle in office['Avg'] if cycle['cycle'] == 'Cycle C'][0]['value'])
        self.assertEqual(405, [cycle for cycle in office['Avg'] if cycle['cycle'] == 'Cycle D'][0]['value'])

        self.assertEqual(110, [cycle for cycle in office['Max'] if cycle['cycle'] == 'Cycle A'][0]['value'])
        self.assertEqual(310, [cycle for cycle in office['Max'] if cycle['cycle'] == 'Cycle C'][0]['value'])
        self.assertEqual(410, [cycle for cycle in office['Max'] if cycle['cycle'] == 'Cycle D'][0]['value'])

        self.assertEqual(100, [cycle for cycle in office['Min'] if cycle['cycle'] == 'Cycle A'][0]['value'])
        self.assertEqual(300, [cycle for cycle in office['Min'] if cycle['cycle'] == 'Cycle C'][0]['value'])
        self.assertEqual(400, [cycle for cycle in office['Min'] if cycle['cycle'] == 'Cycle D'][0]['value'])

        self.assertEqual(210, [cycle for cycle in office['Sum'] if cycle['cycle'] == 'Cycle A'][0]['value'])
        self.assertEqual(610, [cycle for cycle in office['Sum'] if cycle['cycle'] == 'Cycle C'][0]['value'])
        self.assertEqual(810, [cycle for cycle in office['Sum'] if cycle['cycle'] == 'Cycle D'][0]['value'])

        self.assertEqual(2, [cycle for cycle in office['Count'] if cycle['cycle'] == 'Cycle A'][0]['value'])
        self.assertEqual(2, [cycle for cycle in office['Count'] if cycle['cycle'] == 'Cycle C'][0]['value'])
        self.assertEqual(2, [cycle for cycle in office['Count'] if cycle['cycle'] == 'Cycle D'][0]['value'])

    def test_evaluation_endpoint_extra_col(self):
        response = self.client.get(
            reverse('api:v3:data_views-evaluate', args=[self.data_view2.id]) + '?organization_id=' + str(self.org.id)
        )
        data = json.loads(response.content)
        data = data['data']['data']['extra_col']
        three_properties = data['filter_groups']['three_properties']

        self.assertEqual(1100, [cycle for cycle in three_properties['Avg'] if cycle['cycle']=='Cycle A'][0]['value'])
        self.assertEqual(2100, [cycle for cycle in three_properties['Avg'] if cycle['cycle']=='Cycle B'][0]['value'])
        self.assertEqual(3100, [cycle for cycle in three_properties['Avg'] if cycle['cycle']=='Cycle C'][0]['value'])
        self.assertEqual(4100, [cycle for cycle in three_properties['Avg'] if cycle['cycle']=='Cycle D'][0]['value'])

        self.assertEqual(1200, [cycle for cycle in three_properties['Max'] if cycle['cycle']=='Cycle A'][0]['value'])
        self.assertEqual(2200, [cycle for cycle in three_properties['Max'] if cycle['cycle']=='Cycle B'][0]['value'])
        self.assertEqual(3200, [cycle for cycle in three_properties['Max'] if cycle['cycle']=='Cycle C'][0]['value'])
        self.assertEqual(4200, [cycle for cycle in three_properties['Max'] if cycle['cycle']=='Cycle D'][0]['value'])

        self.assertEqual(1000, [cycle for cycle in three_properties['Min'] if cycle['cycle']=='Cycle A'][0]['value'])
        self.assertEqual(2000, [cycle for cycle in three_properties['Min'] if cycle['cycle']=='Cycle B'][0]['value'])
        self.assertEqual(3000, [cycle for cycle in three_properties['Min'] if cycle['cycle']=='Cycle C'][0]['value'])
        self.assertEqual(4000, [cycle for cycle in three_properties['Min'] if cycle['cycle']=='Cycle D'][0]['value'])

        self.assertEqual(3300, [cycle for cycle in three_properties['Sum'] if cycle['cycle']=='Cycle A'][0]['value'])
        self.assertEqual(6300, [cycle for cycle in three_properties['Sum'] if cycle['cycle']=='Cycle B'][0]['value'])
        self.assertEqual(9300, [cycle for cycle in three_properties['Sum'] if cycle['cycle']=='Cycle C'][0]['value'])
        self.assertEqual(12300, [cycle for cycle in three_properties['Sum'] if cycle['cycle']=='Cycle D'][0]['value'])

        self.assertEqual(3, [cycle for cycle in three_properties['Count'] if cycle['cycle']=='Cycle A'][0]['value'])
        self.assertEqual(3, [cycle for cycle in three_properties['Count'] if cycle['cycle']=='Cycle B'][0]['value'])
        self.assertEqual(3, [cycle for cycle in three_properties['Count'] if cycle['cycle']=='Cycle C'][0]['value'])
        self.assertEqual(3, [cycle for cycle in three_properties['Count'] if cycle['cycle']=='Cycle D'][0]['value'])

        four_properties = data['filter_groups']['four_properties']

        self.assertEqual(825, [cycle for cycle in four_properties['Avg'] if cycle['cycle']=='Cycle A'][0]['value'])
        self.assertEqual(1575, [cycle for cycle in four_properties['Avg'] if cycle['cycle']=='Cycle B'][0]['value'])
        self.assertEqual(2325, [cycle for cycle in four_properties['Avg'] if cycle['cycle']=='Cycle C'][0]['value'])
        self.assertEqual(3075, [cycle for cycle in four_properties['Avg'] if cycle['cycle']=='Cycle D'][0]['value'])

        self.assertEqual(1200, [cycle for cycle in four_properties['Max'] if cycle['cycle']=='Cycle A'][0]['value'])
        self.assertEqual(2200, [cycle for cycle in four_properties['Max'] if cycle['cycle']=='Cycle B'][0]['value'])
        self.assertEqual(3200, [cycle for cycle in four_properties['Max'] if cycle['cycle']=='Cycle C'][0]['value'])
        self.assertEqual(4200, [cycle for cycle in four_properties['Max'] if cycle['cycle']=='Cycle D'][0]['value'])

        self.assertEqual(0, [cycle for cycle in four_properties['Min'] if cycle['cycle']=='Cycle A'][0]['value'])
        self.assertEqual(0, [cycle for cycle in four_properties['Min'] if cycle['cycle']=='Cycle B'][0]['value'])
        self.assertEqual(0, [cycle for cycle in four_properties['Min'] if cycle['cycle']=='Cycle C'][0]['value'])
        self.assertEqual(0, [cycle for cycle in four_properties['Min'] if cycle['cycle']=='Cycle D'][0]['value'])

        self.assertEqual(3300, [cycle for cycle in four_properties['Sum'] if cycle['cycle']=='Cycle A'][0]['value'])
        self.assertEqual(6300, [cycle for cycle in four_properties['Sum'] if cycle['cycle']=='Cycle B'][0]['value'])
        self.assertEqual(9300, [cycle for cycle in four_properties['Sum'] if cycle['cycle']=='Cycle C'][0]['value'])
        self.assertEqual(12300, [cycle for cycle in four_properties['Sum'] if cycle['cycle']=='Cycle D'][0]['value'])

        self.assertEqual(4, [cycle for cycle in four_properties['Count'] if cycle['cycle']=='Cycle A'][0]['value'])
        self.assertEqual(4, [cycle for cycle in four_properties['Count'] if cycle['cycle']=='Cycle B'][0]['value'])
        self.assertEqual(4, [cycle for cycle in four_properties['Count'] if cycle['cycle']=='Cycle C'][0]['value'])
        self.assertEqual(4, [cycle for cycle in four_properties['Count'] if cycle['cycle']=='Cycle D'][0]['value'])


    def test_evaluation_endpoint_derived_col(self):
        response = self.client.get(
            reverse('api:v3:data_views-evaluate', args=[self.data_view3.id]) + '?organization_id=' + str(self.org.id)
        )
        data = json.loads(response.content)
        data = data['data']['data'][self.dc_column.column_name]['filter_groups'][self.data_view3.filter_groups[0]['name']]

        # ex:
        # Cycle A
        # site_eui = 10, 11, 12, 13
        # dc       = 20, 21, 22, 23
        # Cycle B
        # site_eui = 20, 21, 22, 23
        # dc       = 30, 31, 32, 33
        self.assertEqual(21.5, [cycle for cycle in data['Avg'] if cycle['cycle'] == 'Cycle A'][0]['value'])
        self.assertEqual(31.5, [cycle for cycle in data['Avg'] if cycle['cycle'] == 'Cycle B'][0]['value'])

        self.assertEqual(23, [cycle for cycle in data['Max'] if cycle['cycle'] == 'Cycle A'][0]['value'])
        self.assertEqual(33, [cycle for cycle in data['Max'] if cycle['cycle'] == 'Cycle B'][0]['value'])

        self.assertEqual(20, [cycle for cycle in data['Min'] if cycle['cycle'] == 'Cycle A'][0]['value'])
        self.assertEqual(30, [cycle for cycle in data['Min'] if cycle['cycle'] == 'Cycle B'][0]['value'])

        self.assertEqual(86, [cycle for cycle in data['Sum'] if cycle['cycle'] == 'Cycle A'][0]['value'])
        self.assertEqual(126, [cycle for cycle in data['Sum'] if cycle['cycle'] == 'Cycle B'][0]['value'])

        self.assertEqual(4, [cycle for cycle in data['Count'] if cycle['cycle'] == 'Cycle A'][0]['value'])
        self.assertEqual(4, [cycle for cycle in data['Count'] if cycle['cycle'] == 'Cycle B'][0]['value'])

        self.assertEqual(20, data['views_by_id'][str(self.vw_office10.id)][0]['value'])
        self.assertEqual(31, data['views_by_id'][str(self.vw_office21.id)][0]['value'])
        self.assertEqual(22, data['views_by_id'][str(self.vw_retail12.id)][0]['value'])
        self.assertEqual(32, data['views_by_id'][str(self.vw_retail22.id)][0]['value'])
