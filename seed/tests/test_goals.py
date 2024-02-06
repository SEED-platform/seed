# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json
from datetime import datetime

from django.urls import reverse_lazy

from seed.landing.models import SEEDUser as User
from seed.models import Column, Goal, GoalNote
from seed.test_helpers.fake import (
    FakeColumnFactory,
    FakeCycleFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory
)
from seed.tests.util import AccessLevelBaseTestCase
from seed.utils.organizations import create_organization


class GoalViewTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.root_owner_user)
        self.column_factory = FakeColumnFactory(organization=self.org)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)

        # cycles
        self.cycle1 = self.cycle_factory.get_cycle(start=datetime(2001, 1, 1), end=datetime(2002, 1, 1))
        self.cycle2 = self.cycle_factory.get_cycle(start=datetime(2002, 1, 1), end=datetime(2003, 1, 1))
        self.cycle3 = self.cycle_factory.get_cycle(start=datetime(2003, 1, 1), end=datetime(2004, 1, 1))

        self.root_ali = self.org.root
        self.child_ali = self.org.root.get_children().first()

        # columns
        extra_eui = Column.objects.create(
            table_name='PropertyState',
            column_name='extra_eui',
            organization=self.org,
            is_extra_data=True,
        )
        extra_area = Column.objects.create(
            table_name='PropertyState',
            column_name='extra_area',
            organization=self.org,
            is_extra_data=True,
        )

        # properties
        # property_details_{property}{cycle}
        property_details_11 = self.property_state_factory.get_details()
        property_details_11['source_eui'] = 1
        property_details_11['gross_floor_area'] = 2
        property_details_11['extra_data'] = {'extra_eui': '10', 'extra_area': '20'}

        property_details_13 = self.property_state_factory.get_details()
        property_details_13['source_eui'] = 3
        property_details_13['source_eui_weather_normalized'] = 4
        property_details_13['gross_floor_area'] = 5
        property_details_13['extra_data'] = {'extra_eui': 20, 'extra_area': 50}

        property_details_31 = self.property_state_factory.get_details()
        property_details_31['source_eui'] = 6
        property_details_31['gross_floor_area'] = 7
        property_details_31['extra_data'] = {'extra_eui': 'abcd', 'extra_area': 'xyz'}

        property_details_33 = self.property_state_factory.get_details()
        property_details_33['source_eui'] = 8
        property_details_33['source_eui_weather_normalized'] = 9
        property_details_33['gross_floor_area'] = 10
        property_details_33['extra_data'] = {'extra_eui': 40, 'extra_area': 100}

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
        self.view21 = self.property_view_factory.get_property_view(prprty=self.property3, state=self.state_31, cycle=self.cycle1)
        self.view33 = self.property_view_factory.get_property_view(prprty=self.property3, state=self.state_33, cycle=self.cycle3)

        self.root_goal = Goal.objects.create(
            organization=self.org,
            baseline_cycle=self.cycle1,
            current_cycle=self.cycle3,
            access_level_instance=self.root_ali,
            eui_column1=Column.objects.get(organization=self.org.id, column_name='source_eui_weather_normalized'),
            eui_column2=Column.objects.get(organization=self.org.id, column_name='source_eui'),
            eui_column3=Column.objects.get(organization=self.org.id, column_name='site_eui'),
            area_column=Column.objects.get(organization=self.org.id, column_name='gross_floor_area'),
            target_percentage=20,
            name='root_goal'
        )
        self.child_goal = Goal.objects.create(
            organization=self.org,
            baseline_cycle=self.cycle1,
            current_cycle=self.cycle3,
            access_level_instance=self.child_ali,
            eui_column1=Column.objects.get(organization=self.org.id, column_name='source_eui_weather_normalized'),
            eui_column2=Column.objects.get(organization=self.org.id, column_name='source_eui'),
            eui_column3=None,
            area_column=Column.objects.get(organization=self.org.id, column_name='gross_floor_area'),
            target_percentage=20,
            name='child_goal'
        )

        self.child_goal_extra = Goal.objects.create(
            organization=self.org,
            baseline_cycle=self.cycle1,
            current_cycle=self.cycle3,
            access_level_instance=self.child_ali,
            eui_column1=extra_eui,
            eui_column2=None,
            eui_column3=None,
            area_column=extra_area,
            target_percentage=20,
            name='child_goal_extra'
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
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200
        assert len(response.json()['goals']) == 3

        self.login_as_child_member()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200
        assert len(response.json()['goals']) == 2

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
        assert response.status_code == 403
        assert Goal.objects.count() == goal_count

        url = reverse_lazy('api:v3:goals-detail', args=[self.child_goal.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 403
        assert Goal.objects.count() == goal_count

        # valid
        self.login_as_root_member()
        url = reverse_lazy('api:v3:goals-detail', args=[self.child_goal.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 204
        assert Goal.objects.count() == goal_count - 1

    def test_goal_create(self):
        goal_count = Goal.objects.count()
        url = reverse_lazy('api:v3:goals-list') + '?organization_id=' + str(self.org.id)
        goal_columns = [
            'placeholder',
            Column.objects.get(organization=self.org.id, column_name='source_eui_weather_normalized').id,
            Column.objects.get(organization=self.org.id, column_name='source_eui').id,
            Column.objects.get(organization=self.org.id, column_name='site_eui').id,
            Column.objects.get(organization=self.org.id, column_name='gross_floor_area').id,
        ]

        def reset_goal_data(name):
            return {
                'organization': self.org.id,
                'baseline_cycle': self.cycle1.id,
                'current_cycle': self.cycle3.id,
                'access_level_instance': self.child_ali.id,
                'eui_column1': goal_columns[1],
                'eui_column2': goal_columns[2],
                'eui_column3': goal_columns[3],
                'area_column': goal_columns[4],
                'target_percentage': 20,
                'name': name
            }
        goal_data = reset_goal_data('child_goal 2')

        # leaves have invalid permissions
        self.login_as_child_member()
        response = self.client.post(
            url,
            data=json.dumps(goal_data),
            content_type='application/json'
        )
        assert response.status_code == 403
        assert Goal.objects.count() == goal_count

        goal_data['access_level_instance'] = self.root_ali.id
        response = self.client.post(
            url,
            data=json.dumps(goal_data),
            content_type='application/json'
        )
        assert response.status_code == 403
        assert Goal.objects.count() == goal_count

        self.login_as_root_member()
        response = self.client.post(
            url,
            data=json.dumps(goal_data),
            content_type='application/json'
        )
        assert response.status_code == 201
        assert Goal.objects.count() == goal_count + 1
        goal_count = Goal.objects.count()

        # invalid data
        goal_data['access_level_instance'] = self.child_ali.id
        goal_data['baseline_cycle'] = 999
        goal_data['eui_column1'] = 998
        response = self.client.post(url, data=json.dumps(goal_data), content_type='application/json')
        assert response.status_code == 400
        errors = response.json()
        assert errors['name'] == ['goal with this name already exists.']
        assert errors['baseline_cycle'] == ['Invalid pk "999" - object does not exist.']
        assert errors['eui_column1'] == ['Invalid pk "998" - object does not exist.']
        assert Goal.objects.count() == goal_count

        # cycles must be unique
        goal_data = reset_goal_data('child_goal 3')
        goal_data['current_cycle'] = self.cycle1.id

        response = self.client.post(url, data=json.dumps(goal_data), content_type='application/json')
        assert response.status_code == 400
        assert response.json()['non_field_errors'] == ['Cycles must be unique.']

        # columns must be unique
        goal_data = reset_goal_data('child_goal 3')
        goal_data['eui_column2'] = goal_columns[1]

        response = self.client.post(url, data=json.dumps(goal_data), content_type='application/json')
        assert response.status_code == 400
        assert response.json()['non_field_errors'] == ['Columns must be unique.']

        # missing data
        goal_data = reset_goal_data('')
        goal_data.pop('name')
        goal_data.pop('baseline_cycle')
        goal_data.pop('eui_column1')
        response = self.client.post(url, data=json.dumps(goal_data), content_type='application/json')
        assert response.status_code == 400
        errors = response.json()
        assert errors['name'] == ['This field is required.']
        assert errors['baseline_cycle'] == ['This field is required.']
        assert errors['eui_column1'] == ['This field is required.']

        # column2 and 3 are optional
        goal_data = reset_goal_data('child_goal 3')
        goal_data['eui_column2'] = None
        goal_data['eui_column3'] = None
        response = self.client.post(url, data=json.dumps(goal_data), content_type='application/json')
        assert response.status_code == 201
        assert response.json()['eui_column1'] == goal_columns[1]
        assert response.json()['eui_column2'] is None
        assert response.json()['eui_column3'] is None
        assert Goal.objects.count() == goal_count + 1

        # incorrect org
        goal_data = reset_goal_data('wrong org goal')
        goal_data['organization'] = self.org2.id
        response = self.client.post(url, data=json.dumps(goal_data), content_type='application/json')
        assert response.json()['non_field_errors'] == ['Organization mismatch.']

    def test_goal_update(self):
        original_goal = Goal.objects.get(id=self.child_goal.id)

        # invalid permission
        self.login_as_child_member()
        url = reverse_lazy('api:v3:goals-detail', args=[self.child_goal.id]) + '?organization_id=' + str(self.org.id)
        goal_data = {
            'baseline_cycle': self.cycle2.id,
            'target_percentage': 99,
        }
        response = self.client.put(url, data=json.dumps(goal_data), content_type='application/json')
        assert response.status_code == 403

        # valid permissions
        self.login_as_root_member()
        response = self.client.put(url, data=json.dumps(goal_data), content_type='application/json')
        assert response.status_code == 200
        assert response.json()['target_percentage'] == 99
        assert response.json()['baseline_cycle'] == self.cycle2.id
        assert response.json()['eui_column1'] == original_goal.eui_column1.id

        # unexpected fields are ignored
        goal_data = {
            'name': 'child_goal y',
            'baseline_cycle': self.cycle1.id,
            'unexpected': 'invalid'
        }
        response = self.client.put(url, data=json.dumps(goal_data), content_type='application/json')
        assert response.json()['name'] == 'child_goal y'
        assert response.json()['baseline_cycle'] == self.cycle1.id
        assert response.json()['eui_column1'] == original_goal.eui_column1.id
        assert 'extra_data' not in response.json()

        # invalid data
        goal_data = {
            'eui_column1': 999,
            'baseline_cycle': 999,
            'target_percentage': 999,
        }
        response = self.client.put(url, data=json.dumps(goal_data), content_type='application/json')
        errors = response.json()['errors']
        assert errors['eui_column1'] == ['Invalid pk "999" - object does not exist.']
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

        # with extra data
        url = reverse_lazy('api:v3:goals-portfolio-summary', args=[self.child_goal_extra.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.get(url, content_type='application/json')
        summary = response.json()
        exp_summary = {
            'baseline': {
                'cycle_name': '2001 Annual',
                'total_kbtu': 200,
                'total_sqft': 20,
                'weighted_eui': 10
            },
            'current': {
                'cycle_name': '2003 Annual',
                'total_kbtu': 5000,
                'total_sqft': 150,
                'weighted_eui': 33},
            'eui_change': -229,
            'sqft_change': 86
        }

        assert summary == exp_summary

class GoalNoteViewTests(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.root_owner_user)
        self.column_factory = FakeColumnFactory(organization=self.org)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)

        # cycles
        self.cycle1 = self.cycle_factory.get_cycle(start=datetime(2001, 1, 1), end=datetime(2002, 1, 1))
        self.cycle2 = self.cycle_factory.get_cycle(start=datetime(2002, 1, 1), end=datetime(2003, 1, 1))

        # access level instances
        self.root_ali = self.org.root
        self.child_ali = self.org.root.get_children().first()

        # properties
        self.property1 = self.property_factory.get_property(access_level_instance=self.child_ali)
        self.property2 = self.property_factory.get_property(access_level_instance=self.child_ali)

        state_details= self.property_state_factory.get_details()
        self.state_11 = self.property_state_factory.get_property_state(**state_details)
        self.state_12 = self.property_state_factory.get_property_state(**state_details)
        self.state_21 = self.property_state_factory.get_property_state(**state_details)
        self.state_22 = self.property_state_factory.get_property_state(**state_details)

        self.view11 = self.property_view_factory.get_property_view(prprty=self.property1, state=self.state_11, cycle=self.cycle1)
        self.view12 = self.property_view_factory.get_property_view(prprty=self.property1, state=self.state_12, cycle=self.cycle2)
        self.view21 = self.property_view_factory.get_property_view(prprty=self.property2, state=self.state_21, cycle=self.cycle1)
        self.view22 = self.property_view_factory.get_property_view(prprty=self.property2, state=self.state_22, cycle=self.cycle2)

        # goals
        goal_details = {
            'organization': self.org,
            'baseline_cycle': self.cycle1,
            'current_cycle': self.cycle2,            
            'access_level_instance': None,
            'eui_column1': Column.objects.get(organization=self.org.id, column_name='source_eui'),
            'eui_column2': None,
            'eui_column3': None,
            'area_column': Column.objects.get(organization=self.org.id, column_name='gross_floor_area'),
            'target_percentage': 20,
            'name': 'name'
        }
        root_details = goal_details 
        root_details['name'] = 'root_goal'
        root_details['access_level_instance'] = self.root_ali
        self.root_goal = Goal.objects.create(**root_details)

        child_details = goal_details
        child_details['name'] = 'child_goal1'
        child_details['access_level_instance'] = self.child_ali
        self.child_goal1 = Goal.objects.create(**child_details)
        child_details['name'] = 'child_goal2'
        self.child_goal2 = Goal.objects.create(**child_details)

        # goal notes 
        note_details = {
            'goal': self.root_goal,
            'property': self.property1,
            'question': 1,
            'resolution': 'resolution1',
            'passed_checks': False,
            'new_or_acquired': False
        }
        self.note_p1_grt = GoalNote.objects.create(**note_details)
        note_details['goal'] = self.child_goal1
        self.note_p1_gch1 = GoalNote.objects.create(**note_details)
        note_details['goal'] = self.child_goal2
        self.note_p1_gch2 = GoalNote.objects.create(**note_details)
        note_details['property'] = self.property2
        self.note_p2_gch2 = GoalNote.objects.create(**note_details)

    def test_goal_note_list(self):
        self.login_as_child_member()
        url = reverse_lazy('api:v3:goal_notes-list', args=[self.child_goal1.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200
        assert len(response.json()['data']) == 1
        assert response.json()['data'][0]['goal'] == self.child_goal1.id

        url = reverse_lazy('api:v3:goal_notes-list', args=[self.child_goal2.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200
        assert len(response.json()['data']) == 2
        assert response.json()['data'][0]['goal'] == self.child_goal2.id


        url = reverse_lazy('api:v3:goal_notes-list', args=[self.root_goal.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200
        assert len(response.json()['data']) == 0

        self.login_as_root_member()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200
        assert len(response.json()['data']) == 1

    def test_goal_note_retrieve(self):
        self.login_as_child_member()
        url = reverse_lazy('api:v3:goal_notes-detail', args=[self.root_goal.id, self.note_p1_grt.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 404 
        assert response.json()['message'] == 'No such resource.'

        self.login_as_root_member()
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 200
        goal_note = response.json()
        assert goal_note['id'] == self.note_p1_grt.id
        assert goal_note['property'] == self.property1.id
        assert goal_note['goal'] == self.root_goal.id
        assert goal_note['resolution'] == 'resolution1'

    def test_goal_note_create(self):
        assert GoalNote.objects.count() == 4
        goal_note_data = {
            'goal': self.root_goal.id,
            'property': self.property2.id,
            'question': 3,
            'resolution': '',
            'passed_checks': False,
            'new_or_acquired': False
        }
        
        self.login_as_child_member()
        url = reverse_lazy('api:v3:goal_notes-list', args=[self.root_goal.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.post(
            url,
            data=json.dumps(goal_note_data),
            content_type='application/json'
        )
        assert response.status_code == 404

        self.login_as_root_member()
        response = self.client.post(
            url,
            data=json.dumps(goal_note_data),
            content_type='application/json'
        )

        assert response.status_code == 201
        goal_note = response.json()
        assert goal_note['property'] == self.property2.id
        assert goal_note['goal'] == self.root_goal.id
        assert goal_note['resolution'] == ''
        assert goal_note['question'] == 3

        assert GoalNote.objects.count() == 5
        # INVALID DATA TESTING ?

    def test_goal_note_delete(self):
        goal_note_count = GoalNote.objects.count()

        self.login_as_child_member()
        url = reverse_lazy('api:v3:goal_notes-detail', args=[self.root_goal.id, self.note_p1_grt.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 404
        assert GoalNote.objects.count() == goal_note_count

        url = reverse_lazy('api:v3:goal_notes-detail', args=[self.child_goal1.id, self.note_p1_gch1.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.delete(url, content_type='application/json')
        assert response.status_code == 204
        assert GoalNote.objects.count() == goal_note_count - 1
