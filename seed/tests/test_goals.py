"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
from datetime import datetime

from django.urls import reverse_lazy

from seed.landing.models import SEEDUser as User
from seed.models import Column, Goal, GoalStandard, GoalNote, HistoricalNote, DataReport
from seed.test_helpers.fake import (
    FakeColumnFactory,
    FakeCycleFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
)
from seed.tests.util import AccessLevelBaseTestCase, GoalStandardTestCase
from seed.utils.organizations import create_organization


class GoalViewTests(GoalStandardTestCase):
    def setUp(self):
        super().setUp()

    def test_goal_list(self):
        url = reverse_lazy("api:v3:goals-list", args=[self.root_data_report.id]) + "?organization_id=" + str(self.org.id)
        self.login_as_root_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        assert len(response.json()) == 1

        self.login_as_child_member()
        url = reverse_lazy("api:v3:goals-list", args=[self.child_data_report.id]) + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_goal_retrieve(self):
        self.login_as_child_member()
        url = reverse_lazy("api:v3:goals-detail", args=[self.child_data_report.id, self.child_goal.id]) + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        goal = response.json()
        assert goal["id"] == self.child_goal.id
        assert goal["current_cycle_property_view_ids"] == [self.view13.id, self.view33.id]

        url = reverse_lazy("api:v3:goals-detail", args=[self.child_data_report.id, -1]) + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 404
        assert response.json()["message"] == "No such resource."

        url = reverse_lazy("api:v3:goals-detail", args=[self.root_data_report.id, self.root_goal.id]) + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 404
        assert response.json()["message"] == "No such resource."

        url = reverse_lazy("api:v3:goals-detail", args=[self.child_data_report.id, self.child_goal.id]) + "?organization_id=" + str(self.org2.id)
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 403
        assert response.json()["message"] == "No relationship to organization"


    def test_goal_destroy(self):
        goal_count = Goal.objects.count()

        # invalid permission
        self.login_as_child_member()
        url = reverse_lazy("api:v3:goals-detail", args=[self.root_data_report.id, self.root_goal.id]) + "?organization_id=" + str(self.org.id)
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 403
        assert Goal.objects.count() == goal_count

        url = reverse_lazy("api:v3:goals-detail", args=[self.child_data_report.id, self.child_goal.id]) + "?organization_id=" + str(self.org.id)
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 403
        assert Goal.objects.count() == goal_count


        url = reverse_lazy("api:v3:goals-detail", args=[self.root_data_report.id, self.child_goal.id]) + "?organization_id=" + str(self.org.id)
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 403
        assert Goal.objects.count() == goal_count

        # valid
        self.login_as_root_member()
        url = reverse_lazy("api:v3:goals-detail", args=[self.child_data_report.id, self.child_goal.id]) + "?organization_id=" + str(self.org.id)
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 204
        assert Goal.objects.count() == goal_count - 1

    def test_goal_create(self):
        goal_count = Goal.objects.count()
        goal_note_count = GoalNote.objects.count()
        url = reverse_lazy("api:v3:goals-list", args=[self.child_data_report.id]) + "?organization_id=" + str(self.org.id)
        goal_columns = [
            "placeholder",
            Column.objects.get(organization=self.org.id, column_name="source_eui_weather_normalized").id,
            Column.objects.get(organization=self.org.id, column_name="source_eui").id,
            Column.objects.get(organization=self.org.id, column_name="site_eui").id,
            Column.objects.get(organization=self.org.id, column_name="gross_floor_area").id,
        ]

        def reset_goal_data(name):
            return {
                "eui_column1": goal_columns[1],
                "eui_column2": goal_columns[2],
                "eui_column3": goal_columns[3],
                "area_column": goal_columns[4],
                "name": name,
                "type": "standard",
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
        assert GoalNote.objects.count() == goal_note_count + 2

        goal_count = Goal.objects.count()

        # invalid data
        goal_data["eui_column1"] = 9998
        response = self.client.post(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.status_code == 400
        errors = response.json()
        assert errors == {'eui_column1': ['Invalid pk "9998" - object does not exist.']}
        assert Goal.objects.count() == goal_count

        # columns must be unique
        goal_data = reset_goal_data("child_goal 3")
        goal_data["eui_column2"] = goal_columns[1]
        response = self.client.post(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.status_code == 400
        assert response.json()["non_field_errors"] == ["Columns must be unique."]

        # missing data
        goal_data = reset_goal_data("")
        goal_data.pop("name")
        goal_data.pop("eui_column1")
        response = self.client.post(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.status_code == 400
        errors = response.json()
        assert errors["name"] == ["This field is required."]
        assert errors["eui_column1"] == ["This field is required."]

        # incorrect org
        url = reverse_lazy("api:v3:goals-list", args=[self.child_data_report.id]) + "?organization_id=" + str(self.org2.id)
        goal_data = reset_goal_data("wrong org goal")
        response = self.client.post(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.status_code == 403
        assert response.json()["message"] == "No relationship to organization"

    def test_goal_update(self):
        original_goal = Goal.objects.get(id=self.child_goal.id)
        goal_note_count = GoalNote.objects.count()

        # invalid permission
        self.login_as_child_member()
        url = reverse_lazy("api:v3:goals-detail", args=[self.child_data_report.id, self.child_goal.id]) + "?organization_id=" + str(self.org.id)
        goal_data = {
            "name": "new name",
            "eui_column1": self.eui_column3.id
        }
        response = self.client.put(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.status_code == 403

        # valid permissions
        self.login_as_root_member()
        response = self.client.put(url, data=json.dumps(goal_data), content_type="application/json")
        assert response.status_code == 200
        response = response.json()
        assert response["name"] == "new name"
        assert response["eui_column1"] == self.eui_column3.id
        assert response["area_column"] == self.area_column.id

        # invalid data
        goal_data = {
            "eui_column1": -1,
            "eui_column2": -1,
        }
        response = self.client.put(url, data=json.dumps(goal_data), content_type="application/json")
        errors = response.json()
        assert errors["eui_column1"] == ['Invalid pk "-1" - object does not exist.']
        assert errors["eui_column2"] == ['Invalid pk "-1" - object does not exist.']

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


    def test_goal_data(self):
        self.login_as_root_member()
        url = reverse_lazy("api:v3:goals-data", args=[self.root_data_report.id, self.root_goal.id]) + "?organization_id=" + str(self.org.id)
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
        alphabet = ["a", "c", "b"]
        questions = ["Is this value correct?", "Are these values correct?", "Other or multiple flags; explain in Additional Notes field"]
        booleans = [True, False, True]
        for idx, goal_note in enumerate(self.root_goal.goalnote_set.all()):
            goal_note.resolution = alphabet[idx]
            goal_note.question = questions[idx]
            goal_note.passed_checks = booleans[idx]
            goal_note.new_or_acquired = booleans[idx]
            goal_note.save()

        for idx, historical_note in enumerate(HistoricalNote.objects.filter(property__in=self.root_goal.properties())):
            historical_note.text = alphabet[idx]
            historical_note.save()

        goal_note = self.root_goal.goalnote_set.first()
        goal_note.new_or_acquired = True
        goal_note.passed_checks = True
        goal_note.save()

        # sort resolution ascending
        params = f"?organization_id={self.org.id}&order_by=property__goal_note__resolution"
        path = reverse_lazy("api:v3:goals-data", args=[self.root_data_report.id, self.root_goal.id])
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
        assert resolutions == ["a", "b", "c"]

        # sort resolution descending
        params = f"?organization_id={self.org.id}&order_by=-property__goal_note__resolution"
        url = path + params
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        response = response.json()
        resolutions = [p["goal_note"]["resolution"] for p in response["properties"]]
        assert resolutions == ["c", "b", "a"]

        # sort historical note text
        params = f"?organization_id={self.org.id}&order_by=property__historical_note__text"
        url = path + params
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        response = response.json()
        historical_notes = [p["historical_note"]["text"] for p in response["properties"]]
        assert historical_notes == ["a", "b", "c"]

        # sort question
        params = f"?organization_id={self.org.id}&order_by=property__goal_note__question"
        url = path + params
        response = self.client.put(url, data=json.dumps(data), content_type="application/json")
        response = response.json()
        questions = [p["goal_note"]["question"] for p in response["properties"]]
        assert questions == [
            "Are these values correct?",
            "Is this value correct?",
            "Other or multiple flags; explain in Additional Notes field",
        ]

        # sort passsed checks
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
