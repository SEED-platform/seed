"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json

from django.urls import reverse_lazy

from seed.models import DataReport, Goal, GoalNote
from seed.test_helpers.fake import (
    FakeDataReportFactory,
    FakeGoalFactory,
)
from seed.tests.util import GoalStandardTestCase


class DataReportViewTests(GoalStandardTestCase):
    def setUp(self):
        # see /tests/util.py for setup details
        super().setUp()

    def test_data_report_list(self):
        url = reverse_lazy("api:v3:data_reports-list") + "?organization_id=" + str(self.org.id)
        self.login_as_root_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        assert len(response.json()["data_reports"]) == 2

        self.login_as_child_member()
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        assert len(response.json()["data_reports"]) == 1

    def test_data_report_retrieve(self):
        self.login_as_child_member()
        url = reverse_lazy("api:v3:data_reports-detail", args=[self.child_data_report.id]) + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 200
        data_report = response.json()["data_report"]
        assert data_report["id"] == self.child_data_report.id
        assert len(data_report["goals"]) == 2

        url = reverse_lazy("api:v3:data_reports-detail", args=[9999]) + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 404
        assert response.json()["message"] == "No such resource."

        url = reverse_lazy("api:v3:data_reports-detail", args=[self.root_data_report.id]) + "?organization_id=" + str(self.org.id)
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 404
        assert response.json()["message"] == "No such resource."

    def test_data_report_destroy(self):
        data_report_count = DataReport.objects.count()

        # invalid permission
        self.login_as_child_member()
        url = reverse_lazy("api:v3:data_reports-detail", args=[self.root_data_report.id]) + "?organization_id=" + str(self.org.id)
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 403
        assert DataReport.objects.count() == data_report_count

        # child member is leaf
        url = reverse_lazy("api:v3:data_reports-detail", args=[self.child_data_report.id]) + "?organization_id=" + str(self.org.id)
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 403
        assert DataReport.objects.count() == data_report_count

        # valid
        self.login_as_root_member()
        url = reverse_lazy("api:v3:data_reports-detail", args=[self.child_data_report.id]) + "?organization_id=" + str(self.org.id)
        response = self.client.delete(url, content_type="application/json")
        assert response.status_code == 204
        assert DataReport.objects.count() == data_report_count - 1

    def test_data_report_create(self):
        url = reverse_lazy("api:v3:data_reports-list") + "?organization_id=" + str(self.org.id)
        data_report_count = DataReport.objects.count()
        goal_count = Goal.objects.count()
        goal_note_count = GoalNote.objects.count()

        def reset_data_report_data(name, report_type, goals=[]):
            return {
                "organization": self.org.id,
                "baseline_cycle": self.cycle1.id,
                "current_cycle": self.cycle3.id,
                "access_level_instance": self.child_ali.id,
                "target_percentage": 20,
                "name": name,
                "type": report_type,
                "goals": goals,
            }

        data_report_data = reset_data_report_data("data report 1", "standard")

        # leaves have invalid permissions
        self.login_as_child_member()
        response = self.client.post(url, data=json.dumps(data_report_data), content_type="application/json")
        assert response.status_code == 403
        assert DataReport.objects.count() == data_report_count

        data_report_data["access_level_instance"] = self.root_ali.id
        response = self.client.post(url, data=json.dumps(data_report_data), content_type="application/json")
        assert response.status_code == 403
        assert DataReport.objects.count() == data_report_count

        self.login_as_root_owner()
        response = self.client.post(url, data=json.dumps(data_report_data), content_type="application/json")
        assert response.status_code == 201
        assert DataReport.objects.count() == data_report_count + 1

        # create goals and data report in a single api call
        goals_data = [
            {
                "name": "goal s1",
                "type": "standard",
                "eui_column1": self.eui_column3.id,
                "eui_column2": None,
                "eui_column3": None,
                "area_column": self.area_column.id,
            },
            {
                "name": "goal s2",
                "type": "standard",
                "eui_column1": self.eui_column3.id,
                "eui_column2": None,
                "eui_column3": None,
                "area_column": self.area_column.id,
            },
            {
                "name": "goal t1",
                "type": "transaction",
                "eui_column1": self.eui_column3.id,
                "eui_column2": None,
                "eui_column3": None,
                "area_column": self.area_column.id,
                "transaction_column": self.transaction_column.id,
            },
        ]
        data_report_data = reset_data_report_data("data report 2", "standard", goals_data)
        response = self.client.post(url, data=json.dumps(data_report_data), content_type="application/json")
        assert response.status_code == 201
        assert DataReport.objects.count() == data_report_count + 2
        assert Goal.objects.count() == goal_count + 3
        # 2 properties per goal => 6 new goal notes
        assert GoalNote.objects.count() == goal_note_count + 6

        # incorrect org
        data_report_data = reset_data_report_data("wrong org data_report", "standard")
        data_report_data["organization"] = self.org2.id
        response = self.client.post(url, data=json.dumps(data_report_data), content_type="application/json")
        assert response.json()["non_field_errors"] == ["Organization mismatch."]

    def test_data_report_update(self):
        data_report_factory = FakeDataReportFactory(
            organization=self.org,
            baseline_cycle=self.cycle1,
            current_cycle=self.cycle3,
            access_level_instance=self.child_ali,
        )
        data_report = data_report_factory.get_data_report(name="original name")
        goal_factory = FakeGoalFactory(data_report=data_report)
        goal1 = goal_factory.get_goal(goal_type="standard", name="g1")
        goal2 = goal_factory.get_goal(goal_type="standard", name="g2")
        goal_factory.get_goal(goal_type="transaction", name="g3", transaction_column=self.transaction_column)

        # invalid permission
        self.login_as_child_member()
        url = reverse_lazy("api:v3:data_reports-detail", args=[data_report.id]) + "?organization_id=" + str(self.org.id)
        data_report_data = {
            "name": "new name",
            "baseline_cycle": self.cycle2.id,
            "target_percentage": 99,
            "goals": [{"id": goal1.id, "name": "g1 new", "eui_column1": self.eui_column3.id}, {"id": goal2.id, "name": "g2 new"}],
        }
        response = self.client.put(url, data=json.dumps(data_report_data), content_type="application/json")
        assert response.status_code == 403

        # valid permissions
        self.login_as_root_member()
        response = self.client.put(url, data=json.dumps(data_report_data), content_type="application/json")
        assert response.status_code == 200
        response = response.json()["data"]
        assert response["name"] == "new name"
        assert response["target_percentage"] == 99
        g1, g2, g3 = response["goals"]
        assert g1["name"] == "g1 new"
        assert g1["eui_column1"] == self.eui_column3.id
        assert g2["name"] == "g2 new"
        assert g3["name"] == "g3"
        assert g3["transaction_column"] == self.transaction_column.id

        # add edge cases
        # unexpected fields
        # invalid data

    def test_portfolio_summary(self):
        self.login_as_child_member()
        url = (
            reverse_lazy("api:v3:data_reports-portfolio-summary", args=[self.root_data_report.id]) + "?organization_id=" + str(self.org.id)
        )
        response = self.client.get(url, content_type="application/json")
        assert response.status_code == 404
        assert response.json()["message"] == "No such resource."

        url = (
            reverse_lazy("api:v3:data_reports-portfolio-summary", args=[self.child_data_report.id]) + "?organization_id=" + str(self.org.id)
        )
        response = self.client.get(url, content_type="application/json")
        summaries = response.json()
        # only properties with passed_checks and not new_or_acquired are included in calc

        assert list(summaries.keys()) == [str(self.child_goal.id), str(self.child_goal_extra.id)]
        g1 = summaries[str(self.child_goal.id)]
        g2 = summaries[str(self.child_goal_extra.id)]
        exp_keys = [
            "baseline",
            "total_properties",
            "shared_sqft",
            "total_passing",
            "total_new_or_acquired",
            "passing_committed",
            "passing_shared",
            "current",
            "sqft_change",
            "eui_change",
        ]
        assert list(g1.keys()) == exp_keys
        assert list(g2.keys()) == exp_keys
        assert g1["shared_sqft"] == 15
        assert g2["shared_sqft"] == 150

        for goalnote in self.child_goal.goalnote_set.all():
            goalnote.passed_checks = True
            goalnote.save()

        response = self.client.get(url, content_type="application/json")
        summaries = response.json()

        exp_summary = {
            "baseline": {"cycle_name": "2001 Annual", "total_kbtu": 44, "total_sqft": 9, "weighted_eui": 4},
            "current": {"cycle_name": "2003 Annual", "total_kbtu": 110, "total_sqft": 15, "weighted_eui": 7},
            "eui_change": -75,
            "passing_committed": None,
            "passing_shared": 100,
            "shared_sqft": 15,
            "sqft_change": 40,
            "total_new_or_acquired": 0,
            "total_passing": 2,
            "total_properties": 2,
        }

        assert summaries[str(self.child_goal.id)] == exp_summary

        # with extra data
        for goalnote in self.child_goal_extra.goalnote_set.all():
            goalnote.passed_checks = True
            goalnote.save()

        url = (
            reverse_lazy("api:v3:data_reports-portfolio-summary", args=[self.child_data_report.id]) + "?organization_id=" + str(self.org.id)
        )
        response = self.client.get(url, content_type="application/json")
        summaries = response.json()
        exp_summary = {
            "baseline": {"cycle_name": "2001 Annual", "total_kbtu": 200, "total_sqft": 20, "weighted_eui": 10},
            "current": {"cycle_name": "2003 Annual", "total_kbtu": 5000, "total_sqft": 150, "weighted_eui": 33},
            "eui_change": -229,
            "passing_committed": None,
            "passing_shared": 100,
            "shared_sqft": 150.0,
            "sqft_change": 86,
            "total_new_or_acquired": 0,
            "total_passing": 2,
            "total_properties": 2,
        }

        assert summaries[str(self.child_goal_extra.id)] == exp_summary
