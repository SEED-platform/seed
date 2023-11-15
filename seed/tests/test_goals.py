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
        self.child_ali = self.org.root.get_children().first()

        self.root_goal = Goal.objects.create(
            organization=self.org,
            baseline_cycle=self.cycle1,
            current_cycle=self.cycle3,
            access_level_instance=self.org.root,
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
        assert response.json()['goal']['id'] == self.child_goal.id

        url = reverse_lazy('api:v3:goals-detail', args=[self.root_goal.id]) + '?organization_id=' + str(self.org.id)
        response = self.client.get(url, content_type='application/json')
        assert response.status_code == 404
        assert response.json()['message'] == 'No such resource.'

        