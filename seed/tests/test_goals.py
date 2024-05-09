# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
from datetime import datetime

from django.urls import reverse_lazy

from seed.landing.models import SEEDUser as User
from seed.models import Column, Goal, GoalNote, HistoricalNote
from seed.test_helpers.fake import (
    FakeColumnFactory,
    FakeCycleFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
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
            table_name="PropertyState",
            column_name="extra_eui",
            organization=self.org,
            is_extra_data=True,
        )
        extra_area = Column.objects.create(
            table_name="PropertyState",
            column_name="extra_area",
            organization=self.org,
            is_extra_data=True,
        )

        # properties
        # property_details_{property}{cycle}
        property_details_11 = self.property_state_factory.get_details()
        property_details_11["source_eui"] = 1
        property_details_11["gross_floor_area"] = 2
        property_details_11["extra_data"] = {"extra_eui": "10", "extra_area": "20"}

        property_details_13 = self.property_state_factory.get_details()
        property_details_13["source_eui"] = 3
        property_details_13["source_eui_weather_normalized"] = 4
        property_details_13["gross_floor_area"] = 5
        property_details_13["extra_data"] = {"extra_eui": 20, "extra_area": 50}

        property_details_31 = self.property_state_factory.get_details()
        property_details_31["source_eui"] = 6
        property_details_31["gross_floor_area"] = 7
        property_details_31["extra_data"] = {"extra_eui": "abcd", "extra_area": "xyz"}

        property_details_33 = self.property_state_factory.get_details()
        property_details_33["source_eui"] = 8
        property_details_33["source_eui_weather_normalized"] = 9
        property_details_33["gross_floor_area"] = 10
        property_details_33["extra_data"] = {"extra_eui": 40, "extra_area": 100}

        self.property1 = self.property_factory.get_property(access_level_instance=self.child_ali)
        self.property2 = self.property_factory.get_property(access_level_instance=self.child_ali)
        self.property3 = self.property_factory.get_property(access_level_instance=self.child_ali)
        self.property4 = self.property_factory.get_property(access_level_instance=self.root_ali)

        self.state_11 = self.property_state_factory.get_property_state(**property_details_11)
        self.state_13 = self.property_state_factory.get_property_state(**property_details_13)
        self.state_2 = self.property_state_factory.get_property_state(**property_details_11)
        self.state_31 = self.property_state_factory.get_property_state(**property_details_31)
        self.state_33 = self.property_state_factory.get_property_state(**property_details_33)
        self.state_41 = self.property_state_factory.get_property_state(**property_details_33)

        self.view11 = self.property_view_factory.get_property_view(prprty=self.property1, state=self.state_11, cycle=self.cycle1)
        self.view13 = self.property_view_factory.get_property_view(prprty=self.property1, state=self.state_13, cycle=self.cycle3)
        self.view2 = self.property_view_factory.get_property_view(prprty=self.property2, state=self.state_2, cycle=self.cycle2)
        self.view21 = self.property_view_factory.get_property_view(prprty=self.property3, state=self.state_31, cycle=self.cycle1)
        self.view33 = self.property_view_factory.get_property_view(prprty=self.property3, state=self.state_33, cycle=self.cycle3)
        self.view41 = self.property_view_factory.get_property_view(prprty=self.property4, state=self.state_41, cycle=self.cycle1)

        self.root_goal = Goal.objects.create(
            organization=self.org,
            baseline_cycle=self.cycle1,
            current_cycle=self.cycle3,
            access_level_instance=self.root_ali,
            eui_column1=Column.objects.get(organization=self.org.id, column_name="source_eui_weather_normalized"),
            eui_column2=Column.objects.get(organization=self.org.id, column_name="source_eui"),
            eui_column3=Column.objects.get(organization=self.org.id, column_name="site_eui"),
            area_column=Column.objects.get(organization=self.org.id, column_name="gross_floor_area"),
            target_percentage=20,
            name="root_goal",
        )
        self.child_goal = Goal.objects.create(
            organization=self.org,
            baseline_cycle=self.cycle1,
            current_cycle=self.cycle3,
            access_level_instance=self.child_ali,
            eui_column1=Column.objects.get(organization=self.org.id, column_name="source_eui_weather_normalized"),
            eui_column2=Column.objects.get(organization=self.org.id, column_name="source_eui"),
            eui_column3=None,
            area_column=Column.objects.get(organization=self.org.id, column_name="gross_floor_area"),
            target_percentage=20,
            name="child_goal",
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
            name="child_goal_extra",
        )

        user2_details = {
            "username": "test_user2@demo.com",
            "password": "test_pass2",
            "email": "test_user2@demo.com",
        }
        self.user2 = User.objects.create_superuser(**user2_details)
        self.org2, _, _ = create_organization(self.user2, "org2")

    def test_goal_list(self):
        url = reverse_lazy("api:v3:goals-list") + "?organization_id=" + str(self.org.id)
        self.login_as_root_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        assert len(response.json()["goals"]) == 3

        self.login_as_child_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        assert len(response.json()["goals"]) == 2

    def test_goal_retrieve(self):
        self.login_as_child_member()
        url = reverse_lazy("api:v3:goals-detail", args=[self.child_goal.id]) + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        goal = response.json()["goal"]
        assert goal["id"] == self.child_goal.id
        assert goal["current_cycle_property_view_ids"] == [self.view13.id, self.view33.id]

        url = reverse_lazy("api:v3:goals-detail", args=[999]) + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 404
        assert response.json()["message"] == "No such resource."

        url = reverse_lazy("api:v3:goals-detail", args=[self.root_goal.id]) + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 404
        assert response.json()["message"] == "No such resource."

    def test_goal_destroy(self):
        goal_count = Goal.objects.count()

        # invalid permission
        self.login_as_child_member()
        url = reverse_lazy("api:v3:goals-detail", args=[self.root_goal.id]) + "?organization_id=" + str(self.org.id)
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 403
        assert Goal.objects.count() == goal_count

        url = reverse_lazy("api:v3:goals-detail", args=[self.child_goal.id]) + "?organization_id=" + str(self.org.id)
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 403
        assert Goal.objects.count() == goal_count

        # valid
        self.login_as_root_member()
        url = reverse_lazy("api:v3:goals-detail", args=[self.child_goal.id]) + "?organization_id=" + str(self.org.id)
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 204
        assert Goal.objects.count() == goal_count - 1

    def test_goal_create(self):
        goal_count = Goal.objects.count()
        goal_note_count = GoalNote.objects.count()
        url = reverse_lazy("api:v3:goals-list") + "?organization_id=" + str(self.org.id)
        goal_columns = [
            "placeholder",
            Column.objects.get(organization=self.org.id, column_name="source_eui_weather_normalized").id,
            Column.objects.get(organization=self.org.id, column_name="source_eui").id,
            Column.objects.get(organization=self.org.id, column_name="site_eui").id,
            Column.objects.get(organization=self.org.id, column_name="gross_floor_area").id,
        ]

        def reset_goal_data(name):
            return {
                "organization": self.org.id,
                "baseline_cycle": self.cycle1.id,
                "current_cycle": self.cycle3.id,
                "access_level_instance": self.child_ali.id,
                "eui_column1": goal_columns[1],
                "eui_column2": goal_columns[2],
                "eui_column3": goal_columns[3],
                "area_column": goal_columns[4],
                "target_percentage": 20,
                "name": name,
            }

        goal_data = reset_goal_data("child_goal 2")

        # leaves have invalid permissions
        self.login_as_child_member()
        response = self.client.post(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.status_code == 403
        assert Goal.objects.count() == goal_count

        goal_data["access_level_instance"] = self.root_ali.id
        response = self.client.post(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.status_code == 403
        assert Goal.objects.count() == goal_count

        self.login_as_root_member()
        response = self.client.post(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.status_code == 201
        assert Goal.objects.count() == goal_count + 1
        assert GoalNote.objects.count() == goal_note_count + 3

        goal_count = Goal.objects.count()

        # invalid data
        goal_data["access_level_instance"] = self.child_ali.id
        goal_data["baseline_cycle"] = 999
        goal_data["eui_column1"] = 998
        response = self.client.post(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.status_code == 400
        errors = response.json()
        assert errors["name"] == ["goal with this name already exists."]
        assert errors["baseline_cycle"] == ['Invalid pk "999" - object does not exist.']
        assert errors["eui_column1"] == ['Invalid pk "998" - object does not exist.']
        assert Goal.objects.count() == goal_count

        # cycles must be unique
        goal_data = reset_goal_data("child_goal 3")
        goal_data["current_cycle"] = self.cycle1.id

        response = self.client.post(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.status_code == 400
        assert response.json()["non_field_errors"] == ["Cycles must be unique."]

        # columns must be unique
        goal_data = reset_goal_data("child_goal 3")
        goal_data["eui_column2"] = goal_columns[1]

        response = self.client.post(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.status_code == 400
        assert response.json()["non_field_errors"] == ["Columns must be unique."]

        # missing data
        goal_data = reset_goal_data("")
        goal_data.pop("name")
        goal_data.pop("baseline_cycle")
        goal_data.pop("eui_column1")
        response = self.client.post(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.status_code == 400
        errors = response.json()
        assert errors["name"] == ["This field is required."]
        assert errors["baseline_cycle"] == ["This field is required."]
        assert errors["eui_column1"] == ["This field is required."]

        # column2 and 3 are optional
        goal_data = reset_goal_data("child_goal 3")
        goal_data["eui_column2"] = None
        goal_data["eui_column3"] = None
        response = self.client.post(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.status_code == 201
        assert response.json()["eui_column1"] == goal_columns[1]
        assert response.json()["eui_column2"] is None
        assert response.json()["eui_column3"] is None
        assert Goal.objects.count() == goal_count + 1

        # incorrect org
        goal_data = reset_goal_data("wrong org goal")
        goal_data["organization"] = self.org2.id
        response = self.client.post(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.json()["non_field_errors"] == ["Organization mismatch."]

    def test_goal_update(self):
        original_goal = Goal.objects.get(id=self.child_goal.id)
        goal_note_count = GoalNote.objects.count()

        # invalid permission
        self.login_as_child_member()
        url = reverse_lazy("api:v3:goals-detail", args=[self.child_goal.id]) + "?organization_id=" + str(self.org.id)
        goal_data = {
            "baseline_cycle": self.cycle2.id,
            "target_percentage": 99,
        }
        response = self.client.put(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.status_code == 403

        # valid permissions
        self.login_as_root_member()
        response = self.client.put(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.status_code == 200
        assert response.json()["target_percentage"] == 99
        assert response.json()["baseline_cycle"] == self.cycle2.id
        assert response.json()["eui_column1"] == original_goal.eui_column1.id
        # changing to cycle 2 adds a new property (and goal_note)
        assert GoalNote.objects.count() == goal_note_count + 1

        goal_data = {"baseline_cycle": self.cycle1.id}
        response = self.client.put(url, data=json.dumps(goal_data), content_type="application/json")
        assert GoalNote.objects.count() == goal_note_count

        # unexpected fields are ignored
        goal_data = {"name": "child_goal y", "baseline_cycle": self.cycle2.id, "unexpected": "invalid"}
        response = self.client.put(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.json()["name"] == "child_goal y"
        assert response.json()["baseline_cycle"] == self.cycle2.id
        assert response.json()["eui_column1"] == original_goal.eui_column1.id
        assert "extra_data" not in response.json()

        # invalid data
        goal_data = {
            "eui_column1": -1,
            "baseline_cycle": -1,
            "target_percentage": -1,
        }
        response = self.client.put(url, data=json.dumps(goal_data), content_type="application/json")
        errors = response.json()["errors"]
        assert errors["eui_column1"] == ['Invalid pk "-1" - object does not exist.']
        assert errors["baseline_cycle"] == ['Invalid pk "-1" - object does not exist.']

    def test_goal_note_update(self):
        goal_note = GoalNote.objects.get(goal_id=self.root_goal.id, property_id=self.property4)
        assert goal_note.question is None
        assert goal_note.resolution is None

        goal_note_data = {
            "question": "Do you have data to report?",
            "resolution": "updated res",
        }
        url = (
            reverse_lazy("api:v3:property-goal-notes-detail", args=[self.property4.id, goal_note.id])
            + "?organization_id="
            + str(self.org.id)
        )
        self.login_as_child_member()
        response = self.client.put(url, data=json.dumps(goal_note_data), content_type="application/json")
        assert response.status_code == 404

        self.login_as_root_member()
        response = self.client.put(url, data=json.dumps(goal_note_data), content_type="application/json")
        assert response.status_code == 200
        response_goal = response.json()
        assert response_goal["question"] == "Do you have data to report?"
        assert response_goal["resolution"] == "updated res"

        # reset goal note
        goal_note_data = {
            "question": None,
            "resolution": None,
        }
        response = self.client.put(url, data=json.dumps(goal_note_data), content_type="application/json")
        assert response.status_code == 200
        response_goal = response.json()
        assert response_goal["question"] is None
        assert response_goal["resolution"] is None

        # child user can only update resolution
        self.login_as_child_member()
        goal_note = GoalNote.objects.get(goal_id=self.child_goal.id, property_id=self.property1)
        goal_note_data = {
            "question": "Do you have data to report?",
            "resolution": "updated res",
            "passed_checks": True,
            "new_or_acquired": True,
        }
        url = (
            reverse_lazy("api:v3:property-goal-notes-detail", args=[self.property1.id, goal_note.id])
            + "?organization_id="
            + str(self.org.id)
        )
        response = self.client.put(url, data=json.dumps(goal_note_data), content_type="application/json")
        assert response.status_code == 200
        response_goal = response.json()
        assert response_goal["question"] is None
        assert response_goal["resolution"] == "updated res"
        assert response_goal["passed_checks"] is False
        assert response_goal["new_or_acquired"] is False

    def test_historical_note_update(self):
        self.login_as_child_member()
        assert self.property1.historical_note.text == ""
        url = (
            reverse_lazy("api:v3:property-historical-notes-detail", args=[self.property1.id, self.property1.historical_note.id])
            + "?organization_id="
            + str(self.org.id)
        )
        data = {"property": self.property1.id, "text": "updated text"}
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 200
        assert response.json()["text"] == "updated text"
        assert HistoricalNote.objects.get(property=self.property1).text == "updated text"

    def test_portfolio_summary(self):
        self.login_as_child_member()
        url = reverse_lazy("api:v3:goals-portfolio-summary", args=[self.root_goal.id]) + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 404
        assert response.json()["message"] == "No such resource."

        url = reverse_lazy("api:v3:goals-portfolio-summary", args=[self.child_goal.id]) + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")
        summary = response.json()
        # only properties with passed_checks and not new_or_acquired are included in calc
        exp_summary = {
            "baseline": {"cycle_name": "2001 Annual", "total_sqft": None, "total_kbtu": None, "weighted_eui": None},
            "current": {"cycle_name": "2003 Annual", "total_sqft": None, "total_kbtu": None, "weighted_eui": None},
            "sqft_change": None,
            "eui_change": None
        }

        assert summary == exp_summary

        for goalnote in self.child_goal.goalnote_set.all():
            goalnote.passed_checks = True
            goalnote.save()

        response = self.client.get(url, content_type="application/json")

        exp_summary = {
            "baseline": {"cycle_name": "2001 Annual", "total_kbtu": 44, "total_sqft": 9, "weighted_eui": 4},
            "current": {"cycle_name": "2003 Annual", "total_kbtu": 110, "total_sqft": 15, "weighted_eui": 7},
            "eui_change": -75,
            "sqft_change": 40,
        }

        assert summary == exp_summary

        # with extra data
        url = reverse_lazy("api:v3:goals-portfolio-summary", args=[self.child_goal_extra.id]) + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")
        summary = response.json()
        exp_summary = {
            "baseline": {"cycle_name": "2001 Annual", "total_kbtu": 200, "total_sqft": 20, "weighted_eui": 10},
            "current": {"cycle_name": "2003 Annual", "total_kbtu": 5000, "total_sqft": 150, "weighted_eui": 33},
            "eui_change": -229,
            "sqft_change": 86,
        }

        assert summary == exp_summary
