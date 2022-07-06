# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
import json
from django.test import TestCase
from django.urls import reverse
from seed.models import DataAggregation, User, Column, DerivedColumn, PropertyState, PropertyView
from seed.utils.organizations import create_organization
from django.utils.timezone import get_current_timezone
from datetime import datetime
from pprint import pprint as pp


from seed.test_helpers.fake import (
    FakePropertyStateFactory,
    FakeDerivedColumnFactory,
    FakePropertyViewFactory,
    FakePropertyFactory,
    FakeCycleFactory,
)



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


class DataAggregationEvaluationTests(TestCase):
    """
    Test DataAggregation ability to evaluate various column types
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

        self.column_default = Column.objects.get(column_name='site_eui')
        # need to make this 'extra data'
        self.column_extra = Column.objects.create(
            column_name='extra_column',
            organization=self.org,
            table_name='PropertyState',
            is_extra_data=True,
        )
        # need to create a derived column first
        self.derived_column = DerivedColumn.objects.create(
            name='dc',
            expression='$a + 10',
            organization=self.org,
            inventory_type=0,
        )
        self.derived_column.source_columns.add(self.column_default.id)
        self.dcp = self.derived_column.derivedcolumnparameter_set.first()
        self.dcp.parameter_name = 'a'
        self.dcp.save()

        self.derived_col_factory = FakeDerivedColumnFactory(
            organization=self.org,
            inventory_type=DerivedColumn.PROPERTY_TYPE
        )
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.cycle = self.cycle_factory.get_cycle(
            start=datetime(2010, 10, 10, tzinfo=get_current_timezone()))

        # Create 3 property/state/views 
        state = self.property_state_factory.get_property_state(extra_data={'extra_column': 100})
        property = self.property_factory.get_property()
        self.view1 = PropertyView.objects.create(property=property, cycle=self.cycle, state=state)
        # add extra data
        
        state = self.property_state_factory.get_property_state(extra_data={'extra_column': 200})
        property = self.property_factory.get_property()
        self.view2 = PropertyView.objects.create(property=property, cycle=self.cycle, state=state)

        state = self.property_state_factory.get_property_state(extra_data={'extra_column': 300})
        property = self.property_factory.get_property()
        self.view3 = PropertyView.objects.create(property=property, cycle=self.cycle, state=state)
        
    def test_evaluate_data_aggregation_endpoint_with_standard_columns(self):
        # Test the ability of a DataAggregation to evaluate a collection of standard columns
        # site EUI values: 121, 269, 91

        self.da_avg = DataAggregation.objects.create(name='eui_avg', type=0, column=self.column_default,organization=self.org)
        self.da_cnt = DataAggregation.objects.create(name='eui_count', type=1, column=self.column_default,organization=self.org)
        self.da_max = DataAggregation.objects.create(name='eui_max', type=2, column=self.column_default,organization=self.org)
        self.da_min = DataAggregation.objects.create(name='eui_min', type=3, column=self.column_default,organization=self.org)
        self.da_sum = DataAggregation.objects.create(name='eui_sum', type=4, column=self.column_default,organization=self.org)
        
        self.assertEqual(self.da_avg.evaluate(), {'value': 160.33, 'units': 'kBtu/ft²/year'})
        self.assertEqual(self.da_cnt.evaluate(), {'value': 3, 'units': None})
        self.assertEqual(self.da_max.evaluate(), {'value': 269, 'units': 'kBtu/ft²/year'})
        self.assertEqual(self.da_min.evaluate(), {'value': 91, 'units': 'kBtu/ft²/year'})
        self.assertEqual(self.da_sum.evaluate(), {'value': 481, 'units': 'kBtu/ft²/year'})

    def test_evaluate_data_aggregation_endpoint_with_derived_columns(self):
        # Test the ability of a DataAggregation to evaluate a collection of derived columns
        self.da_avg = DataAggregation.objects.create(name='dc_avg', type=0, column=self.derived_column.column, organization=self.org)
        self.da_cnt = DataAggregation.objects.create(name='dc_count', type=1, column=self.derived_column.column, organization=self.org)
        self.da_max = DataAggregation.objects.create(name='dc_max', type=2, column=self.derived_column.column, organization=self.org)
        self.da_min = DataAggregation.objects.create(name='dc_min', type=3, column=self.derived_column.column, organization=self.org)
        self.da_sum = DataAggregation.objects.create(name='dc_sum', type=4, column=self.derived_column.column, organization=self.org)
        
        self.assertEqual(self.da_avg.evaluate(), {'value': 170.33, 'units': None})
        self.assertEqual(self.da_cnt.evaluate(), {'value': 3, 'units': None})
        self.assertEqual(self.da_max.evaluate(), {'value': 279, 'units': None})
        self.assertEqual(self.da_min.evaluate(), {'value': 101, 'units': None})
        self.assertEqual(self.da_sum.evaluate(), {'value': 511, 'units': None})


    def test_evaluate_data_aggregation_endpoint_with_extra_data_columns(self):
        # Test the ability of a DataAggregation to evaluate a collection of extra data columns

        self.da_avg = DataAggregation.objects.create(name='extra_avg', type=0, column=self.column_extra,organization=self.org)
        self.da_cnt = DataAggregation.objects.create(name='extra_count', type=1, column=self.column_extra,organization=self.org)
        self.da_max = DataAggregation.objects.create(name='extra_max', type=2, column=self.column_extra,organization=self.org)
        self.da_min = DataAggregation.objects.create(name='extra_min', type=3, column=self.column_extra,organization=self.org)
        self.da_sum = DataAggregation.objects.create(name='extra_sum', type=4, column=self.column_extra,organization=self.org)
        
        self.assertEqual(self.da_avg.evaluate(), {'value': 200, 'units': None})
        self.assertEqual(self.da_cnt.evaluate(), {'value': 3, 'units': None})
        self.assertEqual(self.da_max.evaluate(), {'value': 300, 'units': None})
        self.assertEqual(self.da_min.evaluate(), {'value': 100, 'units': None})
        self.assertEqual(self.da_sum.evaluate(), {'value': 600, 'units': None})
