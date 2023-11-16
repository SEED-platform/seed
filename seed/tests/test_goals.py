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
)


class GoalViewTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()

        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.root_owner_user)
        self.column_factory = FakeColumnFactory(organization=self.org)

        # cycles 
        self.cycle1 = self.cycle_factory.get_cycle(start=datetime(2001, 1, 1), end=datetime(2002, 1, 1))
        self.cycle2 = self.cycle_factory.get_cycle(start=datetime(2002, 1, 1), end=datetime(2003, 1, 1))
        self.cycle3 = self.cycle_factory.get_cycle(start=datetime(2003, 1, 1), end=datetime(2004, 1, 1))
        # columns 
        self.column_eui_extra = self.column_factory.get_column('Source EUI - Adjusted to Current Year', is_extra_data=True)
        self.root_ali = self.org.root
        self.child_ali = self.org.root.get_children().first()

        self.root_goal = Goal.objects.create(
            organization=self.org,
            baseline_cycle=self.cycle1,
            current_cycle=self.cycle3,
            access_level_instance=self.root_ali,
            column1=self.column_eui_extra,
            column2=Column.objects.get(column_name='source_eui_weather_normalized'),
            column3=Column.objects.get(column_name='source_eui'),
            target_percentage=20,
            name='root_goal'
        )
        self.child_goal = Goal.objects.create(
            organization=self.org,
            baseline_cycle=self.cycle1,
            current_cycle=self.cycle3,
            access_level_instance=self.child_ali,
            column1=self.column_eui_extra,
            column2=Column.objects.get(column_name='source_eui_weather_normalized'),
            column3=Column.objects.get(column_name='source_eui'),
            target_percentage=20,
            name='child_goal'
        )

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
            self.column_eui_extra.id, 
            Column.objects.get(column_name='source_eui_weather_normalized').id, 
            Column.objects.get(column_name='source_eui').id
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




    
    def test_goal_update(self):
        original_goal = Goal.objects.get(id=self.child_goal.id)

        self.login_as_child_member()
        url = reverse_lazy('api:v3:goals-detail', args=[self.child_goal.id]) + '?organization_id=' + str(self.org.id)
        goal_data = {
            'name': 'child_goal x',
            'baseline_cycle': self.cycle2.id
        }
        response = self.client.put(url, data=json.dumps(goal_data), content_type='application/json')
        assert response.status_code == 200
        assert response.json()['name'] == 'child_goal x'
        assert response.json()['baseline_cycle'] == self.cycle2.id
        assert response.json()['column1'] == original_goal.column1.id

        # invalid permission 
        goal_data = {
            'access_level_instance': self.root_ali.id
        }
        response = self.client.put(url, data=json.dumps(goal_data), content_type='application/json')
        assert response.status_code == 404
        assert response.json()['message'] == 'No such resource.'

        # invalid data

        # extra data