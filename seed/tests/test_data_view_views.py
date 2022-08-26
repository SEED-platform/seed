# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
import json
from datetime import datetime
from weakref import ProxyType
import unittest

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
    PropertyView
)
from seed.models import StatusLabel as Label
from seed.models import User
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
            data_view=self.data_view1,
            column=self.column1,
            aggregations=['Avg', 'Sum'],
            location='axis1',
        )
        self.data_view1_parameter2 = DataViewParameter.objects.create(
            data_view=self.data_view1,
            column=self.column2,
            aggregations=['Max', 'Min'],
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
            data_view=self.data_view2,
            column=self.column3,
            aggregations=['Avg', 'Max', 'Sum'],
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
        data = json.loads(response.content)
        self.assertEqual(2, len(data['data_views']))

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
        data = json.loads(response.content)
        self.assertEqual(3, len(data['data_views']))

        data_view = DataView.objects.get(name='data_view3')
        response = self.client.delete(
            reverse('api:v3:data_views-detail', args=[data_view.id]) + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )

        response = self.client.get(
            reverse('api:v3:data_views-list') + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )
        data = json.loads(response.content)
        self.assertEqual(2, len(data['data_views']))
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
        self.state10 = self.property_state_factory.get_property_state(property_name='state10', property_type='office', site_eui=10 * ureg.eui, total_ghg_emissions=100, extra_data={'extra_col': 1000})
        self.state11 = self.property_state_factory.get_property_state(property_name='state11', property_type='office', site_eui=11 * ureg.eui, total_ghg_emissions=110, extra_data={'extra_col': 1100})
        self.state12 = self.property_state_factory.get_property_state(property_name='state12', property_type='retail', site_eui=12 * ureg.eui, total_ghg_emissions=120, extra_data={'extra_col': 1200})
        self.state13 = self.property_state_factory.get_property_state(property_name='state13', property_type='retail', site_eui=13 * ureg.eui, total_ghg_emissions=130, extra_data={'extra_col': 0})

        self.view10 = PropertyView.objects.create(property=self.office1, cycle=self.cycle1, state=self.state10)
        self.view11 = PropertyView.objects.create(property=self.office2, cycle=self.cycle1, state=self.state11)
        self.view12 = PropertyView.objects.create(property=self.retail3, cycle=self.cycle1, state=self.state12)
        self.view13 = PropertyView.objects.create(property=self.retail4, cycle=self.cycle1, state=self.state13)

        self.state20 = self.property_state_factory.get_property_state(property_name='state20', property_type='office', site_eui=20 * ureg.eui, total_ghg_emissions=200, extra_data={'extra_col': 2000})
        self.state21 = self.property_state_factory.get_property_state(property_name='state21', property_type='office', site_eui=21 * ureg.eui, total_ghg_emissions=210, extra_data={'extra_col': 2100})
        self.state22 = self.property_state_factory.get_property_state(property_name='state22', property_type='retail', site_eui=22 * ureg.eui, total_ghg_emissions=220, extra_data={'extra_col': 2200})
        self.state23 = self.property_state_factory.get_property_state(property_name='state23', property_type='retail', site_eui=23 * ureg.eui, total_ghg_emissions=230, extra_data={'extra_col': 0})

        self.view20 = PropertyView.objects.create(property=self.office1, cycle=self.cycle2, state=self.state20)
        self.view21 = PropertyView.objects.create(property=self.office2, cycle=self.cycle2, state=self.state21)
        self.view22 = PropertyView.objects.create(property=self.retail3, cycle=self.cycle2, state=self.state22)
        self.view23 = PropertyView.objects.create(property=self.retail4, cycle=self.cycle2, state=self.state23)

        self.state30 = self.property_state_factory.get_property_state(property_name='state30', property_type='office', site_eui=30 * ureg.eui, total_ghg_emissions=300, extra_data={'extra_col': 3000})
        self.state31 = self.property_state_factory.get_property_state(property_name='state31', property_type='office', site_eui=31 * ureg.eui, total_ghg_emissions=310, extra_data={'extra_col': 3100})
        self.state32 = self.property_state_factory.get_property_state(property_name='state32', property_type='retail', site_eui=32 * ureg.eui, total_ghg_emissions=320, extra_data={'extra_col': 3200})
        self.state33 = self.property_state_factory.get_property_state(property_name='state33', property_type='retail', site_eui=33 * ureg.eui, total_ghg_emissions=330, extra_data={'extra_col': 0})

        self.view30 = PropertyView.objects.create(property=self.office1, cycle=self.cycle3, state=self.state30)
        self.view31 = PropertyView.objects.create(property=self.office2, cycle=self.cycle3, state=self.state31)
        self.view32 = PropertyView.objects.create(property=self.retail3, cycle=self.cycle3, state=self.state32)
        self.view33 = PropertyView.objects.create(property=self.retail4, cycle=self.cycle3, state=self.state33)

        self.state40 = self.property_state_factory.get_property_state(property_name='state40', property_type='office', site_eui=40 * ureg.eui, total_ghg_emissions=400, extra_data={'extra_col': 4000})
        self.state41 = self.property_state_factory.get_property_state(property_name='state41', property_type='office', site_eui=41 * ureg.eui, total_ghg_emissions=410, extra_data={'extra_col': 4100})
        self.state42 = self.property_state_factory.get_property_state(property_name='state42', property_type='retail', site_eui=42 * ureg.eui, total_ghg_emissions=420, extra_data={'extra_col': 4200})
        self.state43 = self.property_state_factory.get_property_state(property_name='state43', property_type='retail', site_eui=43 * ureg.eui, total_ghg_emissions=430, extra_data={'extra_col': 0})

        self.view40 = PropertyView.objects.create(property=self.office1, cycle=self.cycle4, state=self.state40)
        self.view41 = PropertyView.objects.create(property=self.office2, cycle=self.cycle4, state=self.state41)
        self.view42 = PropertyView.objects.create(property=self.retail3, cycle=self.cycle4, state=self.state42)
        self.view43 = PropertyView.objects.create(property=self.retail4, cycle=self.cycle4, state=self.state43)

        self.data_view1 = DataView.objects.create(
            name='data view 1',
            filter_groups=[
                {'id': 1, 'name': 'office', 'query_dict': QueryDict('property_type__exact=office&site_eui__gt=1')},
                {'id': 2, 'name': 'retail', 'query_dict': QueryDict('property_type__exact=retail&site_eui__gt=1')}
            ],
            organization=self.org)
        self.data_view1.cycles.set([self.cycle1, self.cycle3, self.cycle4])
        self.data_view1_parameter1 = DataViewParameter.objects.create(
            data_view=self.data_view1,
            column=self.site_eui,
            aggregations=['Avg', 'Sum'],
            location='axis1',
        )
        self.data_view1_parameter2 = DataViewParameter.objects.create(
            data_view=self.data_view1,
            column=self.ghg,
            aggregations=['Max', 'Min'],
            location='axis2',
            target='test'
        )

        self.data_view2 = DataView.objects.create(
            name='data view 2',
            filter_groups=[
                {'id': 3, 'name': 'three_properties', 'query_dict': QueryDict('extra_col__gt=1&site_eui__gt=1')},
                {'id': 4, 'name': 'four_properties', 'query_dict': QueryDict('site_eui__gt=1')}
            ],
            organization=self.org)
        self.data_view2.cycles.set([self.cycle1, self.cycle2, self.cycle3, self.cycle4])
        self.data_view2_parameter1 = DataViewParameter.objects.create(
            data_view=self.data_view2,
            column=self.extra_col,
            aggregations=['Avg'],
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
                {'id': 5, 'name': 'dc_filter', 'query_dict': QueryDict('site_eui__gt=1')},
            ],
            organization=self.org)
        self.data_view3.cycles.set([self.cycle1, self.cycle2])
        self.data_view3_parameter1 = DataViewParameter.objects.create(
            data_view=self.data_view3,
            column=self.dc_column,
            aggregations=['Avg'],
            location='axis1',
        )

    def test_evaluation_endpoint_canonical_col(self):

        self.assertEqual(4, len(self.cycle1.propertyview_set.all()))
        self.assertEqual(4, len(self.cycle2.propertyview_set.all()))
        self.assertEqual(4, len(self.cycle3.propertyview_set.all()))
        self.assertEqual(4, len(self.cycle4.propertyview_set.all()))

        response = self.client.put(
            reverse('api:v3:data_views-evaluate', args=[self.data_view1.id]) + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                "columns": [self.site_eui.id, self.ghg.id],
            }),
            content_type='application/json'
        )

        data = json.loads(response.content)
        self.assertEqual('success', data['status'])


        data = data['data']
        fg_office_id = str(self.data_view1.filter_groups[0]['id'])
        fg_retail_id = str(self.data_view1.filter_groups[1]['id'])
        self.assertEqual(['meta', 'views_by_filter_group_id', 'columns_by_id'], list(data.keys()))

        self.assertEqual(['organization', 'data_view'], list(data['meta'].keys()))

        self.assertEqual([fg_office_id, fg_retail_id], list(data['views_by_filter_group_id']))

        office = data['views_by_filter_group_id'][fg_office_id]
        retail = data['views_by_filter_group_id'][fg_retail_id]

        office_view_ids = [self.view10.id, self.view11.id, self.view30.id, self.view31.id, self.view40.id, self.view41.id]
        retail_view_ids = [self.view12.id, self.view13.id, self.view32.id, self.view33.id, self.view42.id, self.view43.id]

        self.assertEqual(office_view_ids, sorted(data['views_by_filter_group_id'][fg_office_id]))
        self.assertEqual(retail_view_ids, sorted(data['views_by_filter_group_id'][fg_retail_id]))

        data = data['columns_by_id']
        self.assertEqual([str(self.site_eui.id), str(self.ghg.id)], list(data.keys()))
        self.assertEqual(['filter_groups_by_id', 'unit'], list(data[str(self.site_eui.id)].keys()))
        self.assertEqual('kBtu/ft²/year', data[str(self.site_eui.id)]['unit'])
        self.assertEqual('t/year', data[str(self.ghg.id)]['unit'])

        office = data[str(self.site_eui.id)]['filter_groups_by_id'][fg_office_id]
        retail = data[str(self.site_eui.id)]['filter_groups_by_id'][fg_retail_id]
        self.assertEqual(['cycles_by_id'], list(office.keys()))
        self.assertEqual(['cycles_by_id'], list(retail.keys()))

        self.assertEqual([str(self.cycle4.id),str(self.cycle3.id),str(self.cycle1.id)], list(office['cycles_by_id'].keys()))
        self.assertEqual([str(self.cycle4.id),str(self.cycle3.id),str(self.cycle1.id)], list(retail['cycles_by_id'].keys()))

        self.assertEqual(['Average', 'Maximum', 'Minimum', 'Sum', 'Count', 'views_by_id'], list(office['cycles_by_id'][str(self.cycle1.id)]))
        self.assertEqual(['Average', 'Maximum', 'Minimum', 'Sum', 'Count', 'views_by_id'], list(office['cycles_by_id'][str(self.cycle4.id)]))
        self.assertEqual(['Average', 'Maximum', 'Minimum', 'Sum', 'Count', 'views_by_id'], list(retail['cycles_by_id'][str(self.cycle1.id)]))
        self.assertEqual(['Average', 'Maximum', 'Minimum', 'Sum', 'Count', 'views_by_id'], list(retail['cycles_by_id'][str(self.cycle4.id)]))

        office_cycle1 = office['cycles_by_id'][str(self.cycle1.id)]
        office_cycle4 = office['cycles_by_id'][str(self.cycle4.id)]

        self.assertEqual(10.5, office_cycle1['Average'])
        self.assertEqual(2, office_cycle1['Count'])
        self.assertEqual(11, office_cycle1['Maximum'])
        self.assertEqual(10, office_cycle1['Minimum'])
        self.assertEqual(21, office_cycle1['Sum'])
        exp = {str(self.view10.id): 10.0, str(self.view11.id): 11.0}
        self.assertEqual(exp, office_cycle1['views_by_id'])

        self.assertEqual(40.5, office_cycle4['Average'])
        self.assertEqual(2, office_cycle4['Count'])
        self.assertEqual(41, office_cycle4['Maximum'])
        self.assertEqual(40, office_cycle4['Minimum'])
        self.assertEqual(81, office_cycle4['Sum'])
        exp = {str(self.view40.id): 40.0, str(self.view41.id): 41.0}
        self.assertEqual(exp, office_cycle4['views_by_id'])

        retail_cycle1 = retail['cycles_by_id'][str(self.cycle1.id)]
        retail_cycle4 = retail['cycles_by_id'][str(self.cycle4.id)]

        self.assertEqual(12.5, retail_cycle1['Average'])
        self.assertEqual(2, retail_cycle1['Count'])
        self.assertEqual(13, retail_cycle1['Maximum'])
        self.assertEqual(12, retail_cycle1['Minimum'])
        self.assertEqual(25, retail_cycle1['Sum'])
        exp = {str(self.view12.id): 12.0, str(self.view13.id): 13.0}
        self.assertEqual(exp, retail_cycle1['views_by_id'])

        self.assertEqual(42.5, retail_cycle4['Average'])
        self.assertEqual(2, retail_cycle4['Count'])
        self.assertEqual(43, retail_cycle4['Maximum'])
        self.assertEqual(42, retail_cycle4['Minimum'])
        self.assertEqual(85, retail_cycle4['Sum'])
        exp = {str(self.view42.id): 42.0, str(self.view43.id): 43.0}
        self.assertEqual(exp, retail_cycle4['views_by_id'])

    def test_evaluation_endpoint_extra_col(self):
        response = self.client.put(
            reverse('api:v3:data_views-evaluate', args=[self.data_view2.id]) + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                "columns": [self.extra_col.id],
            }),
            content_type='application/json'
        )
        data = json.loads(response.content)
        data = data['data']['columns_by_id'][str(self.extra_col.id)]
        cycle1_id = str(self.cycle1.id)
        cycle4_id = str(self.cycle4.id)
        fg_3_id = str(self.data_view2.filter_groups[0]['id'])
        fg_4_id = str(self.data_view2.filter_groups[1]['id'])

        fg3_cycle1 = data['filter_groups_by_id'][fg_3_id]['cycles_by_id'][cycle1_id]
        self.assertEqual(['Average', 'Maximum', 'Minimum', 'Sum', 'Count', 'views_by_id'], list(fg3_cycle1.keys()))
        self.assertEqual(1100, fg3_cycle1['Average'])
        self.assertEqual(3, fg3_cycle1['Count'])
        self.assertEqual(1200, fg3_cycle1['Maximum'])
        self.assertEqual(1000, fg3_cycle1['Minimum'])
        self.assertEqual(3300, fg3_cycle1['Sum'])
        exp = {str(self.view10.id): 1000, str(self.view11.id): 1100, str(self.view12.id): 1200}
        self.assertEqual(exp, fg3_cycle1['views_by_id'])

        fg4_cycle4 = data['filter_groups_by_id'][fg_4_id]['cycles_by_id'][cycle4_id]
        self.assertEqual(['Average', 'Maximum', 'Minimum', 'Sum', 'Count', 'views_by_id'], list(fg4_cycle4.keys()))
        self.assertEqual(3075, fg4_cycle4['Average'])
        self.assertEqual(4, fg4_cycle4['Count'])
        self.assertEqual(4200, fg4_cycle4['Maximum'])
        self.assertEqual(0, fg4_cycle4['Minimum'])
        self.assertEqual(12300, fg4_cycle4['Sum'])
        exp = {str(self.view40.id): 4000, str(self.view41.id): 4100, str(self.view42.id): 4200, str(self.view43.id): 0}
        self.assertEqual(exp, fg4_cycle4['views_by_id'])
       


    def test_evaluation_endpoint_derived_col(self):
        response = self.client.put(
            reverse('api:v3:data_views-evaluate', args=[self.data_view3.id]) + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                "columns": [self.dc_column.id],
            }),
            content_type='application/json'
        )
        data = json.loads(response.content)
        cycle1_data = data['data']['columns_by_id'][str(self.dc_column.id)]['filter_groups_by_id'][str(self.data_view3.filter_groups[0]['id'])]['cycles_by_id'][str(self.cycle1.id)]
        cycle2_data = data['data']['columns_by_id'][str(self.dc_column.id)]['filter_groups_by_id'][str(self.data_view3.filter_groups[0]['id'])]['cycles_by_id'][str(self.cycle2.id)]

        # ex:
        # Cycle A
        # site_eui = 10, 11, 12, 13
        # dc       = 20, 21, 22, 23
        # Cycle B
        # site_eui = 20, 21, 22, 23
        # dc       = 30, 31, 32, 33
        self.assertEqual(21.5, cycle1_data['Average'])
        self.assertEqual(4, cycle1_data['Count'])
        self.assertEqual(23, cycle1_data['Maximum'])
        self.assertEqual(20, cycle1_data['Minimum'])
        self.assertEqual(86, cycle1_data['Sum'])
        exp = {str(self.view10.id): 20.0,str(self.view11.id): 21.0,str(self.view12.id): 22.0,str(self.view13.id): 23.0}
        self.assertEqual(exp, cycle1_data['views_by_id'])

        self.assertEqual(31.5, cycle2_data['Average'])
        self.assertEqual(4, cycle2_data['Count'])
        self.assertEqual(33, cycle2_data['Maximum'])
        self.assertEqual(30, cycle2_data['Minimum'])
        self.assertEqual(126, cycle2_data['Sum'])
        exp = {str(self.view20.id): 30.0,str(self.view21.id): 31.0,str(self.view22.id): 32.0,str(self.view23.id): 33.0}
        self.assertEqual(exp, cycle2_data['views_by_id'])

class DataViewInventoryTests(TestCase):
    """
    Test DataView model's ability to return property views based on filter groups
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

        self.label1 = Label.objects.create(name='label1', super_organization=self.org, color='red')
        self.label2 = Label.objects.create(name='label2', super_organization=self.org, color='blue')
        self.label3 = Label.objects.create(name='label3', super_organization=self.org, color='green')
        self.label4 = Label.objects.create(name='label4', super_organization=self.org, color='green')

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
        self.state10 = self.property_state_factory.get_property_state(property_name='state10', property_type='office', site_eui=10 * ureg.eui, total_ghg_emissions=100, extra_data={'extra_col': 1000})
        self.state11 = self.property_state_factory.get_property_state(property_name='state11', property_type='office', site_eui=11 * ureg.eui, total_ghg_emissions=110, extra_data={'extra_col': 1100})
        self.state12 = self.property_state_factory.get_property_state(property_name='state12', property_type='retail', site_eui=12 * ureg.eui, total_ghg_emissions=120, extra_data={'extra_col': 1200})
        self.state13 = self.property_state_factory.get_property_state(property_name='state13', property_type='retail', site_eui=13 * ureg.eui, total_ghg_emissions=130, extra_data={'extra_col': 0})

        self.view10 = PropertyView.objects.create(property=self.office1, cycle=self.cycle1, state=self.state10)
        self.view11 = PropertyView.objects.create(property=self.office2, cycle=self.cycle1, state=self.state11)
        self.view12 = PropertyView.objects.create(property=self.retail3, cycle=self.cycle1, state=self.state12)
        self.view13 = PropertyView.objects.create(property=self.retail4, cycle=self.cycle1, state=self.state13)
        self.view10.labels.set([self.label1])
        self.view11.labels.set([self.label1, self.label2])
        self.view12.labels.set([self.label1, self.label2, self.label3])
        self.view13.labels.set([self.label3])

        self.state20 = self.property_state_factory.get_property_state(property_name='state20', property_type='office', site_eui=20 * ureg.eui, total_ghg_emissions=200, extra_data={'extra_col': 2000})
        self.state21 = self.property_state_factory.get_property_state(property_name='state21', property_type='office', site_eui=21 * ureg.eui, total_ghg_emissions=210, extra_data={'extra_col': 2100})
        self.state22 = self.property_state_factory.get_property_state(property_name='state22', property_type='retail', site_eui=22 * ureg.eui, total_ghg_emissions=220, extra_data={'extra_col': 2200})
        self.state23 = self.property_state_factory.get_property_state(property_name='state23', property_type='retail', site_eui=23 * ureg.eui, total_ghg_emissions=230, extra_data={'extra_col': 0})

        self.view20 = PropertyView.objects.create(property=self.office1, cycle=self.cycle2, state=self.state20)
        self.view21 = PropertyView.objects.create(property=self.office2, cycle=self.cycle2, state=self.state21)
        self.view22 = PropertyView.objects.create(property=self.retail3, cycle=self.cycle2, state=self.state22)
        self.view23 = PropertyView.objects.create(property=self.retail4, cycle=self.cycle2, state=self.state23)
        self.view20.labels.set([self.label1, self.label2, self.label3])
        self.view21.labels.set([self.label1, self.label2])
        self.view22.labels.set([self.label1, self.label2])
        self.view23.labels.set([self.label1, self.label2])

        self.state30 = self.property_state_factory.get_property_state(property_name='state30', property_type='office', site_eui=30 * ureg.eui, total_ghg_emissions=300, extra_data={'extra_col': 3000})
        self.state31 = self.property_state_factory.get_property_state(property_name='state31', property_type='office', site_eui=31 * ureg.eui, total_ghg_emissions=310, extra_data={'extra_col': 3100})
        self.state32 = self.property_state_factory.get_property_state(property_name='state32', property_type='retail', site_eui=32 * ureg.eui, total_ghg_emissions=320, extra_data={'extra_col': 3200})
        self.state33 = self.property_state_factory.get_property_state(property_name='state33', property_type='retail', site_eui=33 * ureg.eui, total_ghg_emissions=330, extra_data={'extra_col': 0})

        self.view30 = PropertyView.objects.create(property=self.office1, cycle=self.cycle3, state=self.state30)
        self.view31 = PropertyView.objects.create(property=self.office2, cycle=self.cycle3, state=self.state31)
        self.view32 = PropertyView.objects.create(property=self.retail3, cycle=self.cycle3, state=self.state32)
        self.view33 = PropertyView.objects.create(property=self.retail4, cycle=self.cycle3, state=self.state33)

        # no filter, no labels
        self.data_view1 = DataView.objects.create(
            name='data view 1',
            filter_groups=[
            ],
            organization=self.org)
        self.data_view1.cycles.set([self.cycle1, self.cycle3])
        self.data_view1_parameter1 = DataViewParameter.objects.create(
            data_view=self.data_view1,
            column=self.site_eui,
            aggregations=['Avg'],
            location='axis1',
        )

        # filter, no labels
        self.data_view2 = DataView.objects.create(
            name='data view 2',
            filter_groups=[
                {'id': 6, 'name': 'fg1', 'query_dict': QueryDict('extra_col__gt=1&site_eui__gt=1')},
                {'id': 7, 'name': 'fg2', 'query_dict': QueryDict('site_eui__gt=1')}
            ],
            organization=self.org)
        self.data_view2.cycles.set([self.cycle1, self.cycle2, self.cycle3])
        self.data_view2_parameter1 = DataViewParameter.objects.create(
            data_view=self.data_view2,
            column=self.extra_col,
            aggregations=['Avg'],
            location='axis1',
        )

        # filter, labels
        self.data_view3 = DataView.objects.create(
            name='data view 3',
            filter_groups=[
                {'id': 8, 'name': 'fg_and', 'query_dict': QueryDict('extra_col__gt=1'), 'labels': [self.label2.id, self.label3.id], 'label_logic': "and"},
                {'id': 9, 'name': 'fg_or', 'query_dict': QueryDict('extra_col__gt=1'), 'labels': [self.label2.id, self.label3.id], 'label_logic': "or"},
                {'id': 10, 'name': 'fg_exc', 'query_dict': QueryDict('extra_col__gt=1'), 'labels': [self.label3.id, self.label4.id], 'label_logic': "exclude"}
            ],
            organization=self.org)
        self.data_view3.cycles.set([self.cycle1, self.cycle2, self.cycle3])
        self.data_view3_parameter1 = DataViewParameter.objects.create(
            data_view=self.data_view3,
            column=self.extra_col,
            aggregations=['Avg'],
            location='axis1',
        )

    def test_inventory_endpoint(self):
        response = self.client.get(
            reverse('api:v3:data_views-inventory', args=[self.data_view1.id]) + '?organization_id=' + str(self.org.id)
        )
        data = json.loads(response.content)
        self.assertEqual({}, data['data'])

        response = self.client.get(
            reverse('api:v3:data_views-inventory', args=[self.data_view2.id]) + '?organization_id=' + str(self.org.id)
        )
        data = json.loads(response.content)
        data = data['data']

        exp_filter_group_names = [str(fg['id']) for fg in self.data_view2.filter_groups]
        self.assertEqual(list(data.keys()), exp_filter_group_names)

        # check correct views attached to filter group keys 
        fg1_id = str(self.data_view2.filter_groups[0]['id'])
        fg2_id = str(self.data_view2.filter_groups[1]['id'])

        exp = [self.view10.id, self.view11.id, self.view12.id, self.view20.id, self.view21.id, self.view22.id, self.view30.id, self.view31.id, self.view32.id]
        self.assertEqual(exp, sorted(data[fg1_id]))

        exp = [self.view10.id, self.view11.id, self.view12.id, self.view13.id, self.view20.id, self.view21.id, self.view22.id, self.view23.id, self.view30.id, self.view31.id, self.view32.id, self.view33.id]
        self.assertEqual(exp, sorted(data[fg2_id]))

        response = self.client.get(
            reverse('api:v3:data_views-inventory', args=[self.data_view3.id]) + '?organization_id=' + str(self.org.id)
        )
        data = json.loads(response.content)
        data = data['data']

        fg_and_id = str(self.data_view3.filter_groups[0]['id'])
        fg_or_id = str(self.data_view3.filter_groups[1]['id'])
        fg_exc_id = str(self.data_view3.filter_groups[2]['id'])

        exp = [self.view12.id, self.view20.id]
        self.assertEqual(exp, sorted(data[fg_and_id]))

        exp = [self.view11.id, self.view12.id, self.view20.id, self.view21.id, self.view22.id]
        self.assertEqual(exp, sorted(data[fg_or_id]))

        exp = [self.view10.id, self.view11.id, self.view21.id, self.view22.id, self.view30.id, self.view31.id, self.view32.id]
        self.assertEqual(exp, sorted(data[fg_exc_id]))

