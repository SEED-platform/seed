"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
from datetime import datetime

from django.urls import reverse_lazy

from seed.landing.models import SEEDUser as User
from seed.models import Column, CycleGoal, Goal, GoalNote, HistoricalNote
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
        self.view31 = self.property_view_factory.get_property_view(prprty=self.property3, state=self.state_31, cycle=self.cycle1)
        self.view33 = self.property_view_factory.get_property_view(prprty=self.property3, state=self.state_33, cycle=self.cycle3)
        self.view41 = self.property_view_factory.get_property_view(prprty=self.property4, state=self.state_41, cycle=self.cycle1)

        self.root_goal = Goal.objects.create(
            organization=self.org,
            baseline_cycle=self.cycle1,
            access_level_instance=self.root_ali,
            eui_column1=Column.objects.get(organization=self.org.id, column_name="source_eui_weather_normalized"),
            eui_column2=Column.objects.get(organization=self.org.id, column_name="source_eui"),
            eui_column3=Column.objects.get(organization=self.org.id, column_name="site_eui"),
            area_column=Column.objects.get(organization=self.org.id, column_name="gross_floor_area"),
            target_percentage=20,
            name="root_goal",
        )
        self.root_cycle_goal = CycleGoal.objects.create(current_cycle=self.cycle3, goal=self.root_goal)

        self.child_goal = Goal.objects.create(
            organization=self.org,
            baseline_cycle=self.cycle1,
            access_level_instance=self.child_ali,
            eui_column1=Column.objects.get(organization=self.org.id, column_name="source_eui_weather_normalized"),
            eui_column2=Column.objects.get(organization=self.org.id, column_name="source_eui"),
            eui_column3=None,
            area_column=Column.objects.get(organization=self.org.id, column_name="gross_floor_area"),
            target_percentage=20,
            name="child_goal",
        )
        self.child_cycle_goal = CycleGoal.objects.create(current_cycle=self.cycle3, goal=self.child_goal)

        self.child_goal_extra = Goal.objects.create(
            organization=self.org,
            baseline_cycle=self.cycle1,
            access_level_instance=self.child_ali,
            eui_column1=extra_eui,
            eui_column2=None,
            eui_column3=None,
            area_column=extra_area,
            target_percentage=20,
            name="child_goal_extra",
        )
        self.child_cycle_goal_extra = CycleGoal.objects.create(current_cycle=self.cycle3, goal=self.child_goal_extra)

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

        goal_count = Goal.objects.count()

        # invalid data
        goal_data["access_level_instance"] = self.child_ali.id
        goal_data["baseline_cycle"] = 9999
        goal_data["eui_column1"] = 9998
        response = self.client.post(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.status_code == 400
        errors = response.json()
        assert errors["baseline_cycle"] == ['Invalid pk "9999" - object does not exist.']
        assert errors["eui_column1"] == ['Invalid pk "9998" - object does not exist.']
        assert Goal.objects.count() == goal_count

        # name must be unique within organization
        goal_data = reset_goal_data("child_goal 2")
        response = self.client.post(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.status_code == 400
        errors = response.json()
        assert errors["non_field_errors"] == ["The fields organization, name must make a unique set."]

        # cycles must be unique
        # Note: I don't think this is true anymore
        # goal_data = reset_goal_data("child_goal 3")
        # goal_data["current_cycle"] = self.cycle1.id
        # response = self.client.post(url, data=json.dumps(goal_data), content_type="application/json")
        # assert response.status_code == 400
        # assert response.json()["non_field_errors"] == ["Cycles must be unique."]

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

    def test_cycle_goal_create(self):
        cycle_goal_count = CycleGoal.objects.count()
        goal_note_count = GoalNote.objects.count()
        url = reverse_lazy("api:v3:goal-cycles-list", args=[self.root_goal.id]) + "?organization_id=" + str(self.org.id)
        cycle_goal_data = {"current_cycle": self.cycle3.id}

        # leaves have invalid permissions
        self.login_as_child_member()
        response = self.client.post(url, data=json.dumps(cycle_goal_data), content_type="application/json")
        assert response.status_code == 403
        assert CycleGoal.objects.count() == cycle_goal_count

        # login correctly
        self.login_as_root_member()
        response = self.client.post(url, data=json.dumps(cycle_goal_data), content_type="application/json")
        assert response.status_code == 201

        assert CycleGoal.objects.count() == cycle_goal_count + 1
        assert GoalNote.objects.count() == goal_note_count  # goal notes are 1 per goal/property combo (not one per cycle goal)

    def test_goal_update(self):
        original_goal = Goal.objects.get(id=self.child_goal.id)

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

        goal_data = {"baseline_cycle": self.cycle1.id}
        response = self.client.put(url, data=json.dumps(goal_data), content_type="application/json")

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

    def test_partner_approval_always_stores_user(self):
        """Partner approval must always record the approving user — never null."""
        from seed.lib.superperms.orgs.models import OrganizationUser

        self.login_as_root_member()
        url = reverse_lazy("api:v3:goals-detail", args=[self.root_goal.id]) + "?organization_id=" + str(self.org.id)
        org_user = OrganizationUser.objects.get(user=self.root_member_user, organization=self.org)

        # Approve with the org user ID
        goal_data = {
            "partner_note_approval": True,
            "partner_note_approval_user": org_user.id,
        }
        response = self.client.put(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.status_code == 200
        goal = response.json()
        assert goal["partner_note_approval"] is True
        assert goal["partner_note_approval_user"] == org_user.id, "Approval user must be recorded when approving"
        assert "partner_note_approval_user_name" in goal, "Serializer must include partner_note_approval_user_name"
        assert goal["partner_note_approval_user_name"], "partner_note_approval_user_name must be non-empty"

        # Clear approval — user reference should be nulled out
        goal_data = {
            "partner_note_approval": False,
            "partner_note_approval_user": None,
        }
        response = self.client.put(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.status_code == 200
        goal = response.json()
        assert goal["partner_note_approval"] is False
        assert goal["partner_note_approval_user"] is None

        # Approving without a user should be rejected
        goal_data = {
            "partner_note_approval": True,
            "partner_note_approval_user": None,
        }
        response = self.client.put(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.status_code == 400, "Approving without a user should be rejected"

    def test_goal_note_update(self):
        goal_note = GoalNote.objects.get(goal_id=self.root_cycle_goal.goal.id, property_id=self.property4)
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
        goal_note = GoalNote.objects.get(goal_id=self.child_cycle_goal.goal.id, property_id=self.property1)
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
        url = (
            reverse_lazy("api:v3:goal-cycles-portfolio-summary", args=[self.root_goal.id, self.root_cycle_goal.id])
            + "?organization_id="
            + str(self.org.id)
        )
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 404
        assert response.json()["message"] == "No such resource."

        url = (
            reverse_lazy("api:v3:goal-cycles-portfolio-summary", args=[self.child_goal.id, self.child_cycle_goal.id])
            + "?organization_id="
            + str(self.org.id)
        )
        response = self.client.get(url, content_type="application/json")
        summary = response.json()
        # only properties with passed_checks and not new_or_acquired are included in calc
        exp_summary = {
            "baseline_cycle_name": "2001 Annual",
            "baseline_total_kbtu": None,
            "baseline_total_sqft": None,
            "baseline_weighted_eui": None,
            "current_cycle_name": "2003 Annual",
            "current_total_kbtu": None,
            "current_total_sqft": None,
            "current_weighted_eui": None,
            "eui_change": None,
            "passing_committed": None,
            "passing_shared": None,
            "shared_sqft": 15,
            "sqft_change": None,
            "total_new_or_acquired": 0,
            "total_passing": 0,
            "total_properties": 2,
        }
        assert summary == exp_summary

        for goalnote in self.child_cycle_goal.goal.goalnote_set.all():
            goalnote.passed_checks = True
            goalnote.save()

        response = self.client.get(url, content_type="application/json")
        summary = response.json()

        exp_summary = {
            "baseline_cycle_name": "2001 Annual",
            "baseline_total_kbtu": 44,
            "baseline_total_sqft": 9,
            "baseline_weighted_eui": 4,
            "current_cycle_name": "2003 Annual",
            "current_total_kbtu": 110,
            "current_total_sqft": 15,
            "current_weighted_eui": 7,
            "eui_change": -75,
            "passing_committed": None,
            "passing_shared": 100,
            "shared_sqft": 15,
            "sqft_change": 40,
            "total_new_or_acquired": 0,
            "total_passing": 3,  # this was set to 2 before. this cycle must have 3 properties
            "total_properties": 2,
        }

        assert summary == exp_summary

        # with extra data
        for goalnote in self.child_cycle_goal_extra.goal.goalnote_set.all():
            goalnote.passed_checks = True
            goalnote.save()

        url = (
            reverse_lazy("api:v3:goal-cycles-portfolio-summary", args=[self.child_goal_extra.id, self.child_cycle_goal_extra.id])
            + "?organization_id="
            + str(self.org.id)
        )
        response = self.client.get(url, content_type="application/json")
        summary = response.json()
        exp_summary = {
            "baseline_cycle_name": "2001 Annual",
            "baseline_total_kbtu": 200,
            "baseline_total_sqft": 20.0,
            "baseline_weighted_eui": 10,
            "current_cycle_name": "2003 Annual",
            "current_total_kbtu": 5000,
            "current_total_sqft": 150.0,
            "current_weighted_eui": 33,
            "eui_change": -230,
            "passing_committed": None,
            "passing_shared": 100,
            "shared_sqft": 150.0,
            "sqft_change": 87,
            "total_new_or_acquired": 0,
            "total_passing": 3,
            "total_properties": 2,
        }

        assert summary == exp_summary

    def test_goal_data(self):
        self.login_as_root_member()
        url = (
            reverse_lazy("api:v3:goal-cycles-data", args=[self.root_goal.id, self.root_cycle_goal.id])
            + "?organization_id="
            + str(self.org.id)
        )
        data = {
            "goal_id": self.root_goal.id,
            "page": 1,
            "per_page": 50,
            "baseline_first": True,
            "access_level_instance_id": self.org.root.id,
            "related_model_sort": False,
        }
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 200
        data = response.json()
        assert list(data.keys()) == ["pagination", "properties", "property_lookup"]

        data = {
            "goal_id": self.root_goal.id,
            "page": 2,
            "per_page": 1,
            "baseline_first": True,
            "access_level_instance_id": self.org.root.id,
            "related_model_sort": False,
        }
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        data = response.json()
        assert len(data["properties"]) == 1
        assert data["property_lookup"] == {str(self.view31.id): self.property3.id, str(self.view33.id): self.property3.id}

    def test_related_filter(self):
        goal_note_values = {
            self.property1.id: {
                "resolution": "a",
                "question": "Is this value correct?",
                "passed_checks": True,
                "new_or_acquired": True,
            },
            # Property 2 is not in root_goal and will be ignored
            self.property2.id: {
                "resolution": "b",
                "question": "Are these values correct?",
                "passed_checks": False,
                "new_or_acquired": False,
            },
            self.property3.id: {
                "resolution": "c",
                "question": "Other or multiple flags; explain in Additional Notes field",
                "passed_checks": True,
                "new_or_acquired": True,
            },
            self.property4.id: {
                "resolution": "d",
                "question": "Is this other value correct?",
                "passed_checks": False,
                "new_or_acquired": False,
            },
        }

        for goal_note in self.root_cycle_goal.goal.goalnote_set.select_related("property"):
            for field, value in goal_note_values[goal_note.property_id].items():
                setattr(goal_note, field, value)
            goal_note.save()

        historical_note_values = {
            self.property1.id: "x",
            self.property3.id: "y",
            self.property4.id: "z",
        }
        for historical_note in HistoricalNote.objects.filter(property__in=self.root_cycle_goal.properties()):
            historical_note.text = historical_note_values.get(historical_note.property_id)
            historical_note.save()

        # sort resolution ascending
        params = f"?organization_id={self.org.id}&order_by=property__goal_note__resolution"
        path = reverse_lazy("api:v3:goal-cycles-data", args=[self.root_goal.id, self.root_cycle_goal.id])
        url = path + params
        data = {
            "goal_id": self.root_goal.id,
            "page": 1,
            "per_page": 50,
            "baseline_first": True,
            "access_level_instance_id": self.org.root.id,
            "related_model_sort": True,
        }
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 200
        response = response.json()
        resolutions = [p["goal_note"]["resolution"] for p in response["properties"]]
        assert resolutions == ["a", "c", "d"]
        # sort resolution descending
        params = f"?organization_id={self.org.id}&order_by=-property__goal_note__resolution"
        url = path + params
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        response = response.json()
        resolutions = [p["goal_note"]["resolution"] for p in response["properties"]]
        assert resolutions == ["d", "c", "a"]

        # sort historical note text
        params = f"?organization_id={self.org.id}&order_by=-property__historical_note__text"
        url = path + params
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        response = response.json()
        historical_notes = [p["historical_note"]["text"] for p in response["properties"]]
        assert historical_notes == ["z", "y", "x"]

        # sort question
        params = f"?organization_id={self.org.id}&order_by=property__goal_note__question"
        url = path + params
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        response = response.json()
        questions = [p["goal_note"]["question"] for p in response["properties"]]
        assert questions == [
            "Is this other value correct?",
            "Is this value correct?",
            "Other or multiple flags; explain in Additional Notes field",
        ]

        # sort passed checks
        params = f"?organization_id={self.org.id}&order_by=property__goal_note__passed_checks"
        url = path + params
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        response = response.json()
        passed_checks = [p["goal_note"]["passed_checks"] for p in response["properties"]]
        assert passed_checks == [True, True, False]

        # sort new or acquired desc
        params = f"?organization_id={self.org.id}&order_by=-property__goal_note__new_or_acquired"
        url = path + params
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        response = response.json()
        passed_checks = [p["goal_note"]["passed_checks"] for p in response["properties"]]
        assert passed_checks == [False, True, True]


class TransactionGoalViewTests(AccessLevelBaseTestCase):
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

        self.root_ali = self.org.root

        # columns
        transactions = Column.objects.create(
            table_name="PropertyState",
            column_name="transactions",
            organization=self.org,
            is_extra_data=True,
        )

        # properties
        # property_details_{property}{cycle}
        property_details_11 = self.property_state_factory.get_details()
        property_details_11["source_eui"] = 140
        property_details_11["gross_floor_area"] = 2
        property_details_11["extra_data"] = {"transactions": "10"}

        property_details_12 = self.property_state_factory.get_details()
        property_details_12["source_eui"] = 130
        property_details_12["gross_floor_area"] = 5
        property_details_12["extra_data"] = {"transactions": 20}

        property_details_21 = self.property_state_factory.get_details()
        property_details_21["source_eui"] = 120
        property_details_21["gross_floor_area"] = 7
        property_details_21["extra_data"] = {"transactions": "abcd"}

        property_details_22 = self.property_state_factory.get_details()
        property_details_22["source_eui"] = 100
        property_details_22["gross_floor_area"] = 10
        property_details_22["extra_data"] = {"transactions": 40}

        self.property1 = self.property_factory.get_property(access_level_instance=self.root_ali)
        self.property2 = self.property_factory.get_property(access_level_instance=self.root_ali)

        self.state_11 = self.property_state_factory.get_property_state(**property_details_11)
        self.state_12 = self.property_state_factory.get_property_state(**property_details_12)
        self.state_21 = self.property_state_factory.get_property_state(**property_details_21)
        self.state_22 = self.property_state_factory.get_property_state(**property_details_22)

        self.view11 = self.property_view_factory.get_property_view(prprty=self.property1, state=self.state_11, cycle=self.cycle1)
        self.view12 = self.property_view_factory.get_property_view(prprty=self.property1, state=self.state_12, cycle=self.cycle2)
        self.view21 = self.property_view_factory.get_property_view(prprty=self.property2, state=self.state_21, cycle=self.cycle1)
        self.view22 = self.property_view_factory.get_property_view(prprty=self.property2, state=self.state_22, cycle=self.cycle2)

        self.goal = Goal.objects.create(
            organization=self.org,
            baseline_cycle=self.cycle1,
            access_level_instance=self.root_ali,
            eui_column1=Column.objects.get(organization=self.org.id, column_name="source_eui_weather_normalized"),
            eui_column2=Column.objects.get(organization=self.org.id, column_name="source_eui"),
            eui_column3=Column.objects.get(organization=self.org.id, column_name="site_eui"),
            area_column=Column.objects.get(organization=self.org.id, column_name="gross_floor_area"),
            target_percentage=20,
            name="transaction goal",
            type="transaction",
            transactions_column=transactions,
        )
        self.cycle_goal = CycleGoal.objects.create(current_cycle=self.cycle2, goal=self.goal)

        GoalNote.objects.all().update(passed_checks=True)

    def test_portfolio_summary(self):
        url = (
            reverse_lazy("api:v3:goal-cycles-portfolio-summary", args=[self.goal.id, self.cycle_goal.id])
            + "?organization_id="
            + str(self.org.id)
        )
        response = self.client.get(url, content_type="application/json")
        summary = response.json()

        exp_summary = {
            "baseline_cycle_name": "2001 Annual",
            "baseline_total_kbtu": 1120,
            "baseline_total_sqft": 9,
            "baseline_total_transactions": 10,
            "baseline_weighted_eui": 124,
            "baseline_weighted_eui_t": 112,
            "current_cycle_name": "2002 Annual",
            "current_total_kbtu": 1650,
            "current_total_sqft": 15,
            "current_total_transactions": 60,
            "current_weighted_eui": 110,
            "current_weighted_eui_t": 28,
            "eui_change": 11,
            "eui_t_change": 75,
            "passing_committed": None,
            "passing_shared": 100,
            "shared_sqft": 15,
            "sqft_change": 40,
            "total_new_or_acquired": 0,
            "total_passing": 2,
            "total_properties": 2,
            "transactions_change": 83,
        }

        assert summary == exp_summary

    def test_goal_data(self):
        url = reverse_lazy("api:v3:goal-cycles-data", args=[self.goal.id, self.cycle_goal.id]) + "?organization_id=" + str(self.org.id)
        data = {
            "goal_id": self.goal.id,
            "page": 1,
            "per_page": 50,
            "baseline_first": True,
            "access_level_instance_id": self.org.root.id,
            "related_model_sort": False,
        }
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        assert response.status_code == 200
        data = response.json()
        assert list(data.keys()) == ["pagination", "properties", "property_lookup"]
        properties = data["properties"]

        assert properties[0]["baseline_eui_t"] == 28
        assert properties[0]["baseline_transactions"] == 10
        assert properties[0]["current_eui_t"] == 32
        assert properties[0]["current_transactions"] == 20
        assert properties[0]["eui_t_change"] == 12
        assert properties[0]["transactions_change"] == 50

        assert properties[1]["baseline_eui_t"] is None
        assert properties[1]["baseline_transactions"] is None
        assert properties[1]["current_eui_t"] == 25
        assert properties[1]["current_transactions"] == 40
        assert properties[1]["eui_t_change"] is None
        assert properties[1]["transactions_change"] is None
