# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json
from datetime import datetime
from django.urls import reverse_lazy

from seed.models import Column, Goal

from seed.tests.util import AccessLevelBaseTestCase
from seed.test_helpers.fake import (
    FakeColumnFactory,
    FakeCycleFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
)
from seed.landing.models import SEEDUser as User
from seed.utils.organizations import create_organization


class GoalViewTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.root_owner_user)
        self.column_factory = FakeColumnFactory(organization=self.org)
        self.property_factory =  FakePropertyFactory(organization=self.org)
        self.property_view_factory =  FakePropertyViewFactory(organization=self.org)
        self.property_state_factory =  FakePropertyStateFactory(organization=self.org)

        # cycles 
        self.cycle1 = self.cycle_factory.get_cycle(start=datetime(2001, 1, 1), end=datetime(2002, 1, 1))
        self.cycle2 = self.cycle_factory.get_cycle(start=datetime(2002, 1, 1), end=datetime(2003, 1, 1))
        self.cycle3 = self.cycle_factory.get_cycle(start=datetime(2003, 1, 1), end=datetime(2004, 1, 1))
        # columns 
        # self.column_eui_extra = self.column_factory.get_column('Source EUI - Adjusted to Current Year', is_extra_data=True)
        self.root_ali = self.org.root
        self.child_ali = self.org.root.get_children().first()

        # properties
        # property_details_{property}{cycle}
        property_details_11 = self.property_state_factory.get_details()
        property_details_11['source_eui'] = 1
        property_details_11['gross_floor_area'] = 2 
        property_details_13 = self.property_state_factory.get_details()
        property_details_13['source_eui'] = 3
        property_details_13['source_eui_weather_normalized'] = 4 
        property_details_13['gross_floor_area'] = 5 

        property_details_31 = self.property_state_factory.get_details()
        property_details_31['source_eui'] = 6
        property_details_31['gross_floor_area'] = 7 
        property_details_33 = self.property_state_factory.get_details()
        property_details_33['source_eui'] = 8
        property_details_33['source_eui_weather_normalized'] = 9
        property_details_33['gross_floor_area'] = 10

        self.property1 = self.property_factory.get_property(access_level_instance=self.child_ali)
        self.property2 = self.property_factory.get_property(access_level_instance=self.child_ali)
        self.property3 = self.property_factory.get_property(access_level_instance=self.child_ali)

        self.state_11 = self.property_state_factory.get_property_state(**property_details_11)
        self.state_13 = self.property_state_factory.get_property_state(**property_details_13)
        self.state_2 = self.property_state_factory.get_property_state(**property_details_11)
        self.state_31 = self.property_state_factory.get_property_state(**property_details_31)
        self.state_33 = self.property_state_factory.get_property_state(**property_details_33)

        self.view11 = self.property_view_factory.get_property_view(prprty=self.property1, state=self.state_11, cycle=self.cycle1)
        self.view13 = self.property_view_factory.get_property_view(prprty=self.property1, state=self.state_13, cycle=self.cycle3)
        self.view2 = self.property_view_factory.get_property_view(prprty=self.property2, state=self.state_2, cycle=self.cycle2)
        self.view31 = self.property_view_factory.get_property_view(prprty=self.property3, state=self.state_31, cycle=self.cycle1)
        self.view33 = self.property_view_factory.get_property_view(prprty=self.property3, state=self.state_33, cycle=self.cycle3)

        self.root_goal = Goal.objects.create(
            organization=self.org,
            baseline_cycle=self.cycle1,
            current_cycle=self.cycle3,
            access_level_instance=self.root_ali,
            column1=Column.objects.get(organization=self.org.id, column_name='source_eui_weather_normalized'),
            column2=Column.objects.get(organization=self.org.id, column_name='source_eui'),
            column3=Column.objects.get(organization=self.org.id, column_name='site_eui'),
            target_percentage=20,
            name='root_goal'
        )
        self.child_goal = Goal.objects.create(
            organization=self.org,
            baseline_cycle=self.cycle1,
            current_cycle=self.cycle3,
            access_level_instance=self.child_ali,
            column1=Column.objects.get(organization=self.org.id, column_name='source_eui_weather_normalized'),
            column2=Column.objects.get(organization=self.org.id, column_name='source_eui'),
            column3=None,
            target_percentage=20,
            name='child_goal'
        )

        user2_details = {
            'username': 'test_user2@demo.com',
            'password': 'test_pass2',
            'email': 'test_user2@demo.com',
        }
        self.user2 = User.objects.create_superuser(**user2_details)
        self.org2, _, _ = create_organization(self.user2, "org2")


    def test_goal_list(self):
        url = reverse_lazy('api:v3:goals-list') + '?organization_id=' + str(self.org.id)
        self.login_as_root_member()
        response = self.client.get(url, contemt_type='application/json')
        assert response.status_code == 200
        assert len(response.json()['goals']) == 2

        self.login_as_child_member()
        response = self.client.get(url, contemt_type='application/json')
        assert response.status_code == 200
        assert len(response.json()['goals']) == 1
    
    def test_goal_retrieve(self):
        self.login_as_child_member()
        url = reverse_lazy('api:v3:goals-detail', args=[self.child_goal.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200 
        assert response.json()['id'] == self.child_goal.id

        url = reverse_lazy('api:v3:goals-detail', args=[999]) + '?organization_id=' + str(self.org.id)
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 404 
        assert response.json()['message'] == 'No such resource.'

        url = reverse_lazy('api:v3:goals-detail', args=[self.root_goal.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 404
        assert response.json()['message'] == 'No such resource.'

    def test_goal_destroy(self):
        goal_count = Goal.objects.count()
        
        # invalid permission
        self.login_as_child_member()
        url = reverse_lazy('api:v3:goals-detail', args=[self.root_goal.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 404
        assert Goal.objects.count() == goal_count

        # valid
        url = reverse_lazy('api:v3:goals-detail', args=[self.child_goal.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 204
        assert Goal.objects.count() == goal_count - 1

    def test_goal_create(self):
        goal_count = Goal.objects.count()
        url = reverse_lazy('api:v3:goals-list') + '?organization_id=' + str(self.org.id)
        preferred_columns = [
            'placeholder', 
            Column.objects.get(organization=self.org.id, column_name='source_eui_weather_normalized').id, 
            Column.objects.get(organization=self.org.id, column_name='source_eui').id,
            Column.objects.get(organization=self.org.id, column_name='site_eui').id,
        ]
        def reset_goal_data(name):
            return {
                'organization': self.org.id,
                'baseline_cycle': self.cycle1.id,
                'current_cycle': self.cycle3.id,
                'access_level_instance': self.child_ali.id,
                'column1': preferred_columns[1],
                'column2': preferred_columns[2],
                'column3': preferred_columns[3],
                'target_percentage': 20,
                'name': name
            }
        goal_data = reset_goal_data('child_goal 2')

        # success
        self.login_as_child_member()
        response = self.client.post(
            url,
            data=json.dumps(goal_data),
            content_type='application/json'
        )
        assert response.status_code == 201 
        assert Goal.objects.count() == goal_count + 1
        goal_count = Goal.objects.count()

        # invalid permission
        goal_data['access_level_instance'] = self.root_ali.id
        response = self.client.post(
            url,
            data=json.dumps(goal_data),
            content_type='application/json'
        )
        assert response.status_code == 404
        assert Goal.objects.count() == goal_count

        # invalid data
        goal_data['access_level_instance'] = self.child_ali.id
        goal_data['baseline_cycle'] = 999
        goal_data['column1'] = 998
        response = self.client.post(url, data=json.dumps(goal_data), content_type='application/json')
        assert response.status_code == 400
        errors = response.json()
        assert errors['name'] == ['goal with this name already exists.']
        assert errors['baseline_cycle'] == ['Invalid pk "999" - object does not exist.']
        assert errors['column1'] == ['Invalid pk "998" - object does not exist.']
        assert Goal.objects.count() == goal_count

        # cycles must be unique
        goal_data = reset_goal_data('child_goal 3')
        goal_data['current_cycle'] = self.cycle1.id

        response = self.client.post(url, data=json.dumps(goal_data), content_type='application/json')
        assert response.status_code == 400
        assert response.json()['non_field_errors'] == ['Cycles must be unique.']

        # columns must be unique
        goal_data = reset_goal_data('child_goal 3')
        goal_data['column2'] = preferred_columns[1]

        response = self.client.post(url, data=json.dumps(goal_data), content_type='application/json')
        assert response.status_code == 400
        assert response.json()['non_field_errors'] == ['Columns must be unique.']

        # missing data
        goal_data = reset_goal_data('')
        goal_data.pop('name')
        goal_data.pop('baseline_cycle')
        goal_data.pop('column1')
        response = self.client.post(url, data=json.dumps(goal_data), content_type='application/json')
        assert response.status_code == 400
        errors = response.json()
        assert errors['name'] == ['This field is required.']
        assert errors['baseline_cycle'] == ['This field is required.']
        assert errors['column1'] == ['This field is required.']

        # column2 and 3 are optional
        goal_data = reset_goal_data('child_goal 3')
        goal_data['column2'] = None
        goal_data['column3'] = None
        response = self.client.post(url, data=json.dumps(goal_data), content_type='application/json')
        assert response.status_code == 201
        assert response.json()['column1'] == preferred_columns[1]
        assert response.json()['column2'] == None
        assert response.json()['column3'] == None
        assert Goal.objects.count() == goal_count + 1

        # incorrect org
        # SHOULDNT BE ABLE TO ADD A GOAL TO INCORRECT ORG. DECORATOR? VIEW?
        goal_data = reset_goal_data('wrong org goal')
        goal_data['organization'] = self.org2.id
        response = self.client.post(url, data=json.dumps(goal_data), content_type='application/json')
        # x = response
        # breakpoint()

    
    def test_goal_update(self):
        original_goal = Goal.objects.get(id=self.child_goal.id)

        self.login_as_child_member()
        url = reverse_lazy('api:v3:goals-detail', args=[self.child_goal.id]) + '?organization_id=' + str(self.org.id)
        goal_data = {
            'baseline_cycle': self.cycle2.id,
            'target_percentage': 99,
        }
        response = self.client.put(url, data=json.dumps(goal_data), content_type='application/json')
        assert response.status_code == 200
        assert response.json()['target_percentage'] == 99
        assert response.json()['baseline_cycle'] == self.cycle2.id
        assert response.json()['column1'] == original_goal.column1.id

        # invalid permission 
        goal_data = {
            'access_level_instance': self.root_ali.id
        }
        response = self.client.put(url, data=json.dumps(goal_data), content_type='application/json')
        assert response.status_code == 404
        assert response.json()['message'] == 'No such resource.'

        # extra data is ignored
        goal_data = {
            'name': 'child_goal y',
            'baseline_cycle': self.cycle1.id,
            'extra_data': 'invalid'
        }
        response = self.client.put(url, data=json.dumps(goal_data), content_type='application/json')
        assert response.json()['name'] == 'child_goal y'
        assert response.json()['baseline_cycle'] == self.cycle1.id
        assert response.json()['column1'] == original_goal.column1.id
        assert 'extra_data' not in response.json()


        # invalid data  
        goal_data = {
            'column1': 999,
            'baseline_cycle': 999,
            'target_percentage': 999,
        }
        response = self.client.put(url, data=json.dumps(goal_data), content_type='application/json')
        errors = response.json()['errors']
        assert errors['column1'] == ['Invalid pk "999" - object does not exist.']
        assert errors['baseline_cycle'] == ['Invalid pk "999" - object does not exist.']

    def test_portfolio_summary(self):
        self.login_as_child_member()
        url = reverse_lazy('api:v3:goals-portfolio-summary', args=[self.root_goal.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 404 
        assert response.json()['message'] == 'No such resource.'

        url = reverse_lazy('api:v3:goals-portfolio-summary', args=[self.child_goal.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.get(url, content_type='application/json')
        summary = response.json()
        exp_summary = {
            'baseline': {
                'cycle_name': '2001 Annual',
                'total_kbtu': 44,
                'total_sqft': 9,
                'weighted_eui': 4
            },
            'current': {
                'cycle_name': '2003 Annual',
                'total_kbtu': 110,
                'total_sqft': 15,
                'weighted_eui': 7},
            'eui_change': -75,
            'sqft_change': 40
        }

        assert summary == exp_summary


    # NEED TO TEST WITH EXTRA DATA.
    # are data types a problem?